from typing import Annotated
from uuid import UUID
import logging

from fastapi import (
    APIRouter,
    BackgroundTasks,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
)
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator

from app.core.config import AppConfig
from app.core.dependencies import (
    AuthDependency,
    ConfigDependency,
    DBDependency,
    FSDependency,
)
from app.core.project_types import ImportJobStatus, StatementSource
from app.db.statement_import_jobs import StatementImportJob, create_new_job, load_job
from app.import_job_runner import run_job

router = APIRouter(prefix="/statement-imports", tags=["Importing Statements"])

logger = logging.getLogger(__name__)

app_config = AppConfig()

### API Request - Response Models
class StatementImportResponse(BaseModel):
    import_job_id: UUID
    import_job_status: ImportJobStatus


class StatementMetadata(BaseModel):
    file_name: str | None = None
    file_size: int
    content_type: str

    @field_validator("file_size")
    def valid_file_size
    # app_config.MAX_STATEMENT_SIZE

    # model validator: allowed-type. uses multple fields :name for extension, content type for type
    # field validator: file_size
    # computed field: file_name


### Routes
@router.post("", status_code=202, response_model=StatementImportResponse)
def create_import_job(
    user_id: AuthDependency,
    statement_file: Annotated[UploadFile, File()],
    statement_source: Annotated[StatementSource, Form()],
    db: DBDependency,
    file_storage: FSDependency,
    app_config: ConfigDependency,
    background_tasks: BackgroundTasks,
    request: Request,
) -> StatementImportResponse:
    logger.info(
        f"Creating statement import job. {user_id=} | request_id={request.state.request_id} | {statement_source=} | file_name={statement_file.filename or 'N/A'}"
    )

    # Filename is not mandatory for API consumer to provide. In this case we generate it.
    file_name = statement_file.filename or f"{statement_source.value}_statement"

    file_path = file_storage.upload_statement(
        statement_source=statement_source,
        filename=file_name,
        file=statement_file.file,
        user_id=user_id,
        bucket=app_config.STATEMENTS_STORAGE_BUCKET,
    )
    logger.info(f"Statement file uploaded. {file_path=}")

    job = StatementImportJob(
        user_id=user_id, statement_source=statement_source, file_path=file_path
    )
    db_entry = create_new_job(new_job=job, db=db)

    background_tasks.add_task(
        run_job,
        job_id=db_entry.id,
        user_id=user_id,
        db=db,
        file_storage=file_storage,
        app_config=app_config,
    )
    logger.info(
        f"Statement import job scheduled. job_id={db_entry.id} | {statement_source=} | {file_path=}"
    )

    return StatementImportResponse(import_job_id=job.id, import_job_status=job.status)


@router.get("/{import_job_id}", response_model=StatementImportResponse)
def get_import_job(
    user_id: AuthDependency, import_job_id: UUID, db: DBDependency
) -> StatementImportResponse:
    job = load_job(import_job_id, db)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return StatementImportResponse(import_job_id=job.id, import_job_status=job.status)
