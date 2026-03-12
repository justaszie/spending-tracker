import logging
import time
import uuid
from contextlib import asynccontextmanager
from typing import Annotated, Any

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel
from sqlalchemy import Engine
from sqlmodel import SQLModel, create_engine
from starlette.middleware.cors import CORSMiddleware
from supabase import Client, create_client
from supabase_auth.errors import AuthApiError

from app.api.statement_imports import router as imports_router
from app.api.transactions import router as transactions_router
from app.core.config import AppEnvironment, ConfigError, StorageBackendType, app_config
from app.storage.file_storage import (
    LocalFileStorage,
    StorageBackend,
    SupabaseFileStorage,
)

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


def build_db_engine(environment: AppEnvironment) -> Engine | None:
    connection_string = app_config.DB_CONNECTION_STRING

    # DB is required in DEV and PROD environments
    if not connection_string and environment in (
        AppEnvironment.PROD,
        AppEnvironment.DEV,
    ):
        raise ConfigError("Missing database connection string in environment")

    if connection_string:
        engine = create_engine(connection_string)
        SQLModel.metadata.create_all(engine)
        return engine

    return None


def build_supabase_admin(environment: AppEnvironment) -> Client | None:
    supabase_admin = None

    supabase_url = app_config.SUPABASE_URL
    supabase_admin_key = app_config.SUPABASE_ADMIN_KEY

    if environment == AppEnvironment.PROD and not (supabase_url and supabase_admin_key):
        raise ConfigError("Missing Supabase URL / Secret Key in environment")

    if supabase_url and supabase_admin_key:
        supabase_admin = create_client(supabase_url, supabase_admin_key)
        logger.info("Supabase Admin Client Initialized")
        return supabase_admin

    return None


def build_storage(
    environment: AppEnvironment,
    storage_type: StorageBackendType = StorageBackendType.SUPABASE,
    supabase_admin: Client | None = None,
) -> StorageBackend | None:
    if storage_type == StorageBackendType.LOCAL:
        local_root = app_config.LOCAL_STORAGE_ROOT
        return LocalFileStorage(local_root)

    if storage_type == StorageBackendType.SUPABASE:
        if supabase_admin is None and environment in (
            AppEnvironment.DEV,
            AppEnvironment.PROD,
        ):
            raise Exception("Cannot initialize file storage without supabase client")

        if supabase_admin:
            logger.info("Supabase file storage initialized")
            return SupabaseFileStorage(supabase_admin)

    return None


# Instantiating auth service, storage and logging config as part of app startup
@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore
    environment = app_config.APP_ENVIRONMENT

    engine = build_db_engine(environment)
    if engine is not None:
        app.state.db_engine = engine
        logger.info("Database Connection Established")

    supabase_admin = build_supabase_admin(environment)
    if supabase_admin is not None:
        app.state.supabase_admin = supabase_admin
        logger.info("Supabase Admin Client Initialized")

    storage = build_storage(
        environment=environment,
        supabase_admin=supabase_admin,
        storage_type=app_config.STORAGE_BACKEND,
    )
    if storage is not None:
        app.state.file_storage = storage
        logger.info(
            "File storage initialized with backend %s",
            app_config.STORAGE_BACKEND.value,
        )

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
