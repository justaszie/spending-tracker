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
from fastapi.exceptions import RequestValidationError
from pydantic import (
    BaseModel,
    ValidationError,
)

from app.core.dependencies import (
    AuthDependency,
    ConfigDependency,
    DBDependency,
    FSDependency,
)
from app.core.project_types import ImportJobStatus, StatementSource
from app.db.statement_import_jobs import StatementImportJob, create_new_job, load_job
from app.import_job_runner import run_job
from app.statement_validation import StatementMetadata

router = APIRouter(prefix="/statement-imports", tags=["Importing Statements"])

logger = logging.getLogger(__name__)


### API Request - Response Models
class StatementImportResponse(BaseModel):
    import_job_id: UUID
    import_job_status: ImportJobStatus


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
    # If API consumer doesn't provide a filename, generate a generic one
    file_name = statement_file.filename or f"{statement_source.value}_statement"
    file = statement_file.file

    # Validate the uploaded statement file
    try:
        statement_metadata = StatementMetadata(
            source=statement_source,
            file_name=file_name,
            file_size=statement_file.size,
            file_type=statement_file.content_type,
        )
    except ValidationError as e:
        logger.exception("Statement file validation failed")
        raise RequestValidationError(e.errors()) from e

    logger.info(
        f"Creating statement import job. {user_id=} | request_id={request.state.request_id}"
        f"| source={statement_metadata.source} | file_name={statement_metadata.file_name}"
    )
    file_path = file_storage.upload_statement(
        user_id=user_id,
        file=file,
        statement_metadata=statement_metadata,
        storage_bucket=app_config.STATEMENTS_STORAGE_BUCKET,
    )
    logger.info(f"Statement file uploaded. {file_path=}")

    job = StatementImportJob(
        user_id=user_id, statement_source=statement_metadata.source, file_path=file_path
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
        f"Statement import job scheduled. job_id={db_entry.id}"
        f"| statement_source={statement_metadata.source} | {file_path=}"
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
