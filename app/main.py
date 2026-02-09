from contextlib import asynccontextmanager
from typing import Annotated
import logging

from fastapi import (
    APIRouter,
    Depends,
    FastAPI,
    HTTPException,
)
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlmodel import SQLModel, create_engine
from supabase_auth.errors import AuthApiError

from app.api.routes.import_jobs import router as jobs_router
from app.config import AppConfig, AppEnvironment
from app.dependencies import (
    ConfigDependency,
    get_authenticated_user,
)
from app.file_storage import FileStorage
from supabase import create_client

user_creds_auth = HTTPBasic()


# Validate username (email) and password, sign user in and return a JWT token if successful
def validate_user_creds(
    app_config: ConfigDependency,
    creds: Annotated[HTTPBasicCredentials, Depends(user_creds_auth)],
) -> str:
    # Create a supabase client separate from global admin client that uses storage
    supabase_client = create_client(
        app_config.supabase_url, app_config.supabase_anon_key
    )
    try:
        response = supabase_client.auth.sign_in_with_password(
            {
                "email": creds.username,
                "password": creds.password,
            }
        )
    except AuthApiError as e:
        logger.log(logging.WARNING, f"Failed to validate user credentials: {e}")
        raise HTTPException(status_code=401, detail="User credentials invalid")
    if not response.session:
        raise HTTPException(status_code=401, detail="User credentials invalid")

    return response.session.access_token


# Instantiating auth service, storage and logging config as part of app startup
@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore
    # 1. Initialize app config
    # Ignoring type checking. Type checker expects config variables passed as args
    # but they are being read from environment.
    app_config = AppConfig()  # type: ignore
    app.state.app_config = app_config

    # 2. Initialize database client
    connection_string = app_config.db_connection_string
    if not connection_string:
        logger.error("Missing database connection string in environment")
        raise Exception("Missing database connection string in environment")
    engine = create_engine(connection_string)
    SQLModel.metadata.create_all(engine)
    app.state.db_engine = engine

    # 3. Initialize service role supabase client
    supabase_url = app_config.supabase_url
    supabase_admin_key = app_config.supabase_admin_key
    supabase_admin = create_client(supabase_url, supabase_admin_key)
    app.state.supabase_admin = supabase_admin
    logger.info("Supabase Admin Client Initialized")

    # 4. Initialize file storage client
    app.state.file_storage = FileStorage(supabase_admin)
    logger.info("File Storage Initialized")

    # 5. Auth feature flag - skip jwt validation in DEV environment
    if app_config.app_environment == AppEnvironment.DEV:
        app.dependency_overrides[get_authenticated_user] = (
            lambda: app_config.test_user_id
        )

    yield

    # Shutdown
    engine.dispose()


def configure_logging() -> None:
    logging.basicConfig(
        format="[{levelname}] - {asctime} - {name}: {message}",
        style="{",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=logging.INFO,
    )

    logging.getLogger("googleapiclient").setLevel(logging.ERROR)


configure_logging()
logger = logging.getLogger(__name__)

app = FastAPI(lifespan=lifespan)

# Basic routes for health check and auth
core_router = APIRouter()


@core_router.get("/")
def root() -> "str":
    return "HELLO FROM SPENDING TRACKER"


@core_router.post("/auth")
def authenticate_user(
    jwt: Annotated[str, Depends(validate_user_creds)],
) -> JSONResponse:
    return JSONResponse({"access_token": jwt})


api_prefix = AppConfig().V1_API_PREFIX
app.include_router(core_router, prefix=api_prefix)
app.include_router(jobs_router, prefix=api_prefix)
