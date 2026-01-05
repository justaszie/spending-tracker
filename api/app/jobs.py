import datetime as dt
import logging
import uuid

from sqlalchemy.exc import IntegrityError
from sqlmodel import Field, Session, SQLModel

logger = logging.getLogger(__name__)


class IngestJob(SQLModel, table=True):
    __tablename__ = "jobs"

    job_id: uuid.UUID = Field(primary_key=True, default_factory=uuid.uuid4)
    bank: str = Field(nullable=False)
    file_path: str | None = Field(default=None)
    created_at: dt.datetime = Field(nullable=False, default_factory=dt.datetime.now)
    started_at: dt.datetime | None = Field(nullable=True)
    finished_at: dt.datetime | None = Field(nullable=True)
    status: str = Field(nullable=False, default="pending")
    failure_reason: str | None = Field(default=None)
    ingested_txn_count: int | None = Field(default=None)


def create_new_job(new_job: IngestJob, session: Session) -> IngestJob:
    try:
        session.add(new_job)
        session.commit()
        session.refresh(new_job)
        return new_job
    except IntegrityError as e:
        logger.warning(
            f"Duplicate job entry creation attempted "
            f"| Job ID: {new_job.job_id}"
        )
        raise DuplicateEntryError(
            f"Job {new_job.job_id} already exists. "
            f"Use update method to replace it."
        ) from e


def load_job(id: uuid.UUID, session: Session) -> IngestJob | None:
    job = session.get(IngestJob, id)
    return job


class DuplicateEntryError(ValueError):
    pass
