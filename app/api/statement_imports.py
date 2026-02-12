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
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, ValidationError, field_validator, model_validator

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
from app.statement_extractors.registry import allowed_content_types, allowed_file_extensions

router = APIRouter(prefix="/statement-imports", tags=["Importing Statements"])

logger = logging.getLogger(__name__)

app_config = AppConfig()


### API Request - Response Models
class StatementImportResponse(BaseModel):
    import_job_id: UUID
    import_job_status: ImportJobStatus


class StatementFileMetadata(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    file_name: str | None = None
    file_size: int
    content_type: str
    statement_source: StatementSource

    @field_validator("file_size")
    @classmethod
    def valid_file_size(cls, value: int):
        if value <= 0:
            # TODO - how to properly raise the error so that loc property is populated same as for other FastAPI error
            raise ValueError("Statement file can't be empty")

        max_size = app_config.MAX_STATEMENT_SIZE
        if value > max_size:
            raise ValueError(
                f"Statement file can't exceed {max_size / 1024**2}MB. "
                f"Try splitting the statement file into smaller chunks"
            )
        return value

    @model_validator(mode="after")
    def is_valid_type(self) -> "StatementFileMetadata":
        allowed_extensions = allowed_file_extensions(self.statement_source)

        if self.file_name:
            file_extension = self.file_name.split('.')[-1]
            if file_extension.lower() in allowed_extensions:
                return self

        if self.content_type and (
            self.content_type.lower() in allowed_content_types(self.statement_source)
            # Default content type is allowed since we can't predict what values clients can set
            or self.content_type.lower() == "application/octet-stream"
        ):
            return self

        raise ValueError(
            f"Statement file type is not valid for {self.statement_source.value}. "
            f"Supported Types: {allowed_extensions}"
        )


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


    try:
        StatementFileMetadata.model_validate(
            {
                "file_name": statement_file.filename,
                "file_size": statement_file.size,
                "content_type": statement_file.content_type,
                "statement_source": statement_source,
            }
        )
    except ValidationError as e:
        logger.exception("Statement file validation failed")
        raise RequestValidationError(e.errors()) from e

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
