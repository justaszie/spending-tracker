import logging
from contextlib import asynccontextmanager
from typing import Annotated
from uuid import UUID


from fastapi import (
    BackgroundTasks,
    Depends,
    FastAPI,
    Form,
    HTTPException,
    UploadFile,
)
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.responses import JSONResponse
from sqlmodel import create_engine, SQLModel
from supabase import create_client
from supabase_auth.errors import AuthApiError

from app.config import AppConfig
from app.dependencies import (
    AuthDependency,
    ConfigDependency,
    DBDependency,
    FSDependency,
)
from app.db.jobs import IngestJob, create_new_job, load_job
from app.project_types import StatementSource
from app.file_storage import FileStorage
from app.orchestration import run_job


user_creds_auth = HTTPBasic()


# Validate username (email) and password, sign user in and return a JWT token if successful
def validate_user_creds(
    app_config: ConfigDependency,
    creds: Annotated[HTTPBasicCredentials, Depends(user_creds_auth)]
) -> str:
    # Create a supabase client separate from global admin client that uses storage
    supabase_client = create_client(app_config.supabase_url, app_config.supabase_anon_key)
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
    app_config = AppConfig() # type: ignore
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

    yield


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


@app.get("/")
def root() -> "str":
    return "HELLO FROM SPENDING TRACKER"

@app.post("/auth")
def authenticate_user(jwt: Annotated[str, Depends(validate_user_creds)]) -> JSONResponse:
    return JSONResponse({"access_token": jwt})

@app.post("/ingest-jobs", status_code=202)
def create_job(
    user_id: AuthDependency,
    statement_file: UploadFile,
    statement_source: Annotated[StatementSource, Form()],
    db: DBDependency,
    file_storage: FSDependency,
    app_config: ConfigDependency,
    background_tasks: BackgroundTasks,
) -> JSONResponse:
    # Filename is not mandatory for API consumer to provide. In this case we generate it.
    file_name = statement_file.filename or f"{statement_source.value}_statement"

    file_path = file_storage.upload_statement(
        statement_source=statement_source,
        filename=file_name,
        file=statement_file.file,
        user_id=user_id,
        bucket=app_config.statements_storage_bucket,
    )

    job = IngestJob(user_id=user_id, statement_source=statement_source, file_path=file_path)
    db_entry = create_new_job(new_job=job, db=db)

    background_tasks.add_task(
        run_job,
        job_id=db_entry.id,
        user_id=user_id,
        db=db,
        file_storage=file_storage,
        app_config=app_config,
    )

    return JSONResponse({"job_id": str(db_entry.id), "status": db_entry.status})


@app.get("/ingest-jobs/{job_id}")
def get_job(user_id: AuthDependency, job_id: UUID, db: DBDependency) -> JSONResponse:
    job = load_job(job_id, db)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return JSONResponse(
        {
            "job_id": str(job.id),
            "status": job.status,
        }
    )
