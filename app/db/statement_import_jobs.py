import datetime as dt
import logging
import uuid

from sqlalchemy import Engine
from sqlalchemy.exc import IntegrityError
from sqlmodel import Field, Session, SQLModel

from app.core.project_types import ImportJobStatus, StatementSource

logger = logging.getLogger(__name__)


class StatementImportJob(SQLModel, table=True):
    __tablename__ = "statement_import_jobs"  # type: ignore

    id: uuid.UUID = Field(primary_key=True, default_factory=uuid.uuid4)
    statement_source: StatementSource = Field(nullable=False)
    file_path: str = Field(nullable=False)
    created_at: dt.datetime = Field(nullable=False, default_factory=dt.datetime.now)
    updated_at: dt.datetime = Field(nullable=True, default_factory=dt.datetime.now)
    started_at: dt.datetime | None = Field(default=None)
    completed_at: dt.datetime | None = Field(default=None)
    status: ImportJobStatus = Field(nullable=False, default=ImportJobStatus.PENDING)
    failure_reason: str | None = Field(default=None)
    imported_txn_count: int | None = Field(default=None)
    duplicate_txn_count: int | None = Field(default=None)
    user_id: uuid.UUID | None = Field(nullable=True, default=None)


def create_new_job(new_job: StatementImportJob, db: Engine) -> StatementImportJob:
    with Session(db) as session:
        try:
            session.add(new_job)
            session.commit()
            session.refresh(new_job)
            return new_job
        except IntegrityError as e:
            logger.warning(
                f"Duplicate job entry creation attempted | Job ID: {new_job.id}"
            )
            raise DuplicateEntryError(
                f"Job {new_job.id} already exists. Use update method to replace it."
            ) from e


def load_job(job_id: uuid.UUID, db: Engine) -> StatementImportJob | None:
    with Session(db) as session:
        job = session.get(StatementImportJob, job_id)
        return job


def update_job(updated_job: StatementImportJob, db: Engine) -> None:
    with Session(db) as session:
        existing = session.get(StatementImportJob, updated_job.id)
        if existing is None:
            raise ValueError(f"Job not found: id = {updated_job.id}")

        session.add(updated_job)
        session.commit()
        session.refresh(updated_job)


class DuplicateEntryError(ValueError):
    pass
