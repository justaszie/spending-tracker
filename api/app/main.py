import logging
from contextlib import asynccontextmanager
from typing import Annotated
from uuid import UUID


from fastapi import (
    BackgroundTasks,
    FastAPI,
    Form,
    HTTPException,
    UploadFile,
)
from fastapi.responses import JSONResponse
from sqlmodel import create_engine, SQLModel
from supabase import create_client

from app.deps import (
    SettingsDependency,
    get_settings,
    DBDependency,
    FSDependency,
)
from app.db.jobs import IngestJob, create_new_job, load_job
from app.project_types import StatementSource
from app.file_storage import FileStorage
from app.orchestration import run_job


class ConfigException(Exception):
    pass


# Instantiating auth service, storage and logging config as part of app startup
@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore
    app_settings = get_settings()
    connection_string = app_settings.db_connection_string
    if not connection_string:
        logger.error("Missing database connection string in environment")
        raise Exception("Missing database connection string in environment")
    engine = create_engine(connection_string)
    SQLModel.metadata.create_all(engine)
    app.state.db_engine = engine

    supabase_url = app_settings.supabase_url
    supabase_admin_key = app_settings.supabase_admin_key
    app.state.supabase = create_client(supabase_url, supabase_admin_key)
    logger.info("Supabase Client Initialized")

    app.state.file_storage = FileStorage(app.state.supabase)
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


@app.post("/ingest-job", status_code=202)
def create_job(
    statement_file: UploadFile,
    statement_source: Annotated[StatementSource, Form()],
    db: DBDependency,
    file_storage: FSDependency,
    app_settings: SettingsDependency,
    background_tasks: BackgroundTasks,
) -> JSONResponse:
    # Filename is not mandatory for API consumer to provide. In this case we generate it.
    file_name = statement_file.filename or f"{statement_source.value}_statement"

    file_path = file_storage.upload_statement(
        statement_source=statement_source,
        filename=file_name,
        file=statement_file.file,
        user_id=app_settings.test_user_id,
        bucket=app_settings.statements_bucket,
    )

    job = IngestJob(statement_source=statement_source, file_path=file_path)
    db_entry = create_new_job(new_job=job, db=db)

    background_tasks.add_task(
        run_job,
        job_id=str(db_entry.id),
        db=db,
        file_storage=file_storage,
        app_settings=app_settings,
    )

    return JSONResponse({"job_id": str(db_entry.id), "status": db_entry.status})


@app.get("/ingest-job/{job_id}")
def get_job(job_id: UUID, db: DBDependency) -> JSONResponse:
    job = load_job(job_id, db)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return JSONResponse(
        {
            "job_id": str(job.id),
            "status": job.status,
        }
    )
