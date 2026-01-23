import datetime as dt
import logging
import uuid

from sqlalchemy import Engine
from sqlalchemy.exc import IntegrityError
from sqlmodel import Field, Session, SQLModel

from app.project_types import JobStatus, StatementSource

logger = logging.getLogger(__name__)


class IngestJob(SQLModel, table=True):
    __tablename__ = "jobs"

    id: uuid.UUID = Field(primary_key=True, default_factory=uuid.uuid4)
    statement_source: StatementSource = Field(nullable=False)
    file_path: str = Field(nullable=False)
    created_at: dt.datetime = Field(nullable=False, default_factory=dt.datetime.now)
    started_at: dt.datetime | None = Field(default=None)
    finished_at: dt.datetime | None = Field(default=None)
    status: JobStatus = Field(nullable=False, default=JobStatus.PENDING)
    failure_reason: str | None = Field(default=None)
    ingested_txn_count: int | None = Field(default=None)
    duplicate_txn_count: int | None = Field(default=None)


def create_new_job(new_job: IngestJob, db: Engine) -> IngestJob:
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


def load_job(job_id: uuid.UUID, db: Engine) -> IngestJob | None:
    with Session(db) as session:
        job = session.get(IngestJob, job_id)
        return job


def update_job(updated_job: IngestJob, db: Engine) -> None:
    with Session(db) as session:
        session.add(updated_job)
        session.commit()
        session.refresh(updated_job)


class DuplicateEntryError(ValueError):
    pass
