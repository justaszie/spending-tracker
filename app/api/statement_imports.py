from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Form,
    HTTPException,
    UploadFile,
)
from fastapi.responses import JSONResponse

from app.db.statement_import_jobs import StatementImportJob, create_new_job, load_job
from app.dependencies import (
    AuthDependency,
    ConfigDependency,
    DBDependency,
    FSDependency,
)
from app.orchestration import run_job
from app.project_types import StatementSource

router = APIRouter(prefix="/statement-imports", tags=["Importing Statements"])


### API Request - Response Models

### Routes
@router.post("", status_code=202)
def create_import_job(
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

    return JSONResponse({"import_job_id": str(db_entry.id), "import_job_status": db_entry.status})


@router.get("/{import_job_id}")
def get_import_job(user_id: AuthDependency, import_job_id: UUID, db: DBDependency) -> JSONResponse:
    job = load_job(import_job_id, db)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return JSONResponse(
        {
            "import_job_id": str(job.id),
            "import_job_status": job.status,
        }
    )
