import logging
import time
import uuid
from contextlib import asynccontextmanager
from typing import Annotated, Any

from fastapi import (
    APIRouter,
    Depends,
    FastAPI,
    HTTPException,
    Request,
)
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel
from sqlmodel import SQLModel, create_engine
from starlette.middleware.cors import CORSMiddleware
from supabase import create_client
from supabase_auth.errors import AuthApiError

from app.api.statement_imports import router as imports_router
from app.api.transactions import router as transactions_router
from app.core.config import AppEnvironment, ConfigError, PROJECT_ROOT, app_config
from app.storage.file_storage import LocalFileStorage, SupabaseFileStorage

user_creds_auth = HTTPBasic()


# Validate username (email) and password, sign user in and return a JWT token if successful
def validate_user_creds(
    creds: Annotated[HTTPBasicCredentials, Depends(user_creds_auth)],
) -> str:
    # Create a supabase client separate from global admin client that uses storage
    if not app_config.SUPABASE_URL or not app_config.SUPABASE_ANON_KEY:
        raise ConfigError("Missing Supabase URL / Anon Key in environment")

    supabase_client = create_client(
        app_config.SUPABASE_URL, app_config.SUPABASE_ANON_KEY
    )
    try:
        response = supabase_client.auth.sign_in_with_password(
            {
                "email": creds.username,
                "password": creds.password,
            }
        )
    except AuthApiError as e:
        logger.warning(f"Failed to validate user credentials: {e}")
        raise HTTPException(status_code=401, detail="User credentials invalid") from e
    if not response.session:
        raise HTTPException(status_code=401, detail="User credentials invalid")

    return response.session.access_token


# Instantiating auth service, storage and logging config as part of app startup
@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore
    environment = app_config.APP_ENVIRONMENT

    # 1. Initialize database client (optional if environment is not DEV or PROD)
    connection_string = app_config.DB_CONNECTION_STRING

    if connection_string:
        engine = create_engine(connection_string)
        SQLModel.metadata.create_all(engine)
        app.state.db_engine = engine
        logger.info("Database Connection Established")
    elif environment != AppEnvironment.TEST:
        logger.error("Missing database connection string in environment")
        raise ConfigError("Missing database connection string in environment")

    # 2. Initialize service role supabase client (optional if environment is not DEV or PROD)
    supabase_admin = None
    supabase_url = app_config.SUPABASE_URL
    supabase_admin_key = app_config.SUPABASE_ADMIN_KEY
    if supabase_url and supabase_admin_key:
        supabase_admin = create_client(supabase_url, supabase_admin_key)
        app.state.supabase_admin = supabase_admin
        logger.info("Supabase Admin Client Initialized")
    elif environment not in (AppEnvironment.TEST, AppEnvironment.DEV):
        logger.error("Missing Supabase URL / Secret Key in environment")
        raise ConfigError("Missing Supabase URL / Secret Key in environment")

    if environment == AppEnvironment.DEV:
        local_root = app_config.LOCAL_STORAGE_ROOT or PROJECT_ROOT / "local_storage"
        app.state.file_storage = LocalFileStorage(local_root)
        logger.info("Local file storage initialized at %s", local_root)
    elif supabase_admin:
        app.state.file_storage = SupabaseFileStorage(supabase_admin)
        logger.info("Supabase file storage initialized")
    elif environment != AppEnvironment.TEST:
        logger.error("Cannot initialize File Storage without supabase client")
        raise Exception("Cannot initialize File Storage without supabase client")

    logger.info("App is fully initialized")

    yield

    # Shutdown
    if hasattr(app.state, "db_engine"):
        app.state.db_engine.dispose()


# Configure logger format
logging.basicConfig(
    format="[{levelname}] - {asctime} - {name}: {message}",
    style="{",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.INFO,
)
# Custom logging is done to cover the external service calls
logging.getLogger("httpx").disabled = True

logger = logging.getLogger(__name__)

app = FastAPI(lifespan=lifespan)

# Basic routes for health check and auth
core_router = APIRouter()


@core_router.get("/")
def root() -> "str":
    return "Status: OK"


class AccessTokenResponse(BaseModel):
    access_token: str


@core_router.post("/auth", response_model=AccessTokenResponse)
def authenticate_user(
    jwt: Annotated[str, Depends(validate_user_creds)],
) -> AccessTokenResponse:
    return AccessTokenResponse(access_token=jwt)


# CORS Setup: allow all known client domains
cors_origins: list[str] = []
frontend_domain: str | None = app_config.FRONTEND_URL
if frontend_domain:
    cors_origins.append(frontend_domain)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=False,
)

api_prefix = app_config.V1_API_PREFIX
app.include_router(core_router, prefix=api_prefix)
app.include_router(imports_router, prefix=api_prefix)
app.include_router(transactions_router, prefix=api_prefix)


# Middleware to log processed requests
@app.middleware("http")
async def log_request_processed(request: Request, call_next: Any) -> Any:
    start_time = time.perf_counter()
    request_id = uuid.uuid4()
    method = request.method
    path = request.url.path
    logger.info(f"Processing request {request_id}. {method} | {path}")
    # Make request available in the route functions to link it with other events
    request.state.request_id = request_id

    response = await call_next(request)

    status_code = response.status_code
    process_time_ms = (time.perf_counter() - start_time) * 1000

    # Log the processed request
    logger.info(
        f"Request {request_id} processed. {method} | {path} | {status_code} | Duration: {process_time_ms:.2f}ms"
    )

    # Add request id to response header for debugging
    response.headers["X-Request-Id"] = str(request_id)

    return response
