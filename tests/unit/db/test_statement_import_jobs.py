import datetime as dt
import uuid

import pytest
from sqlmodel import Session, select

from app.core.project_types import ImportJobStatus, StatementSource
from app.db.statement_import_jobs import (
    DuplicateEntryError,
    StatementImportJob,
    create_new_job,
    load_job,
    update_job,
)


class TestInitializeJob:
    def test_populates_default_values(self):
        job = StatementImportJob(
            statement_source=StatementSource.REVOLUT,
            file_path="/path/to/statement.csv",
        )

        # Some fields should be automatically populated
        assert isinstance(job.id, uuid.UUID)
        assert isinstance(job.created_at, dt.datetime)
        assert isinstance(job.updated_at, dt.datetime)
        assert job.status == ImportJobStatus.PENDING

        # All other fields should be None by default
        assert job.started_at is None
        assert job.completed_at is None
        assert job.failure_reason is None
        assert job.imported_txn_count is None
        assert job.duplicate_txn_count is None
        assert job.user_id is None


class TestInsertJob:
    def test_inserts_jobs(self, test_db):
        job1 = StatementImportJob(
            statement_source=StatementSource.REVOLUT,
            file_path="/path/to/statement1.xslx",
        )
        job2 = StatementImportJob(
            statement_source=StatementSource.SWEDBANK,
            file_path="/path/to/statement2.csv",
        )

        created1 = create_new_job(new_job=job1, db=test_db)
        created2 = create_new_job(new_job=job2, db=test_db)

        with Session(test_db) as session:
            result = session.exec(select(StatementImportJob)).all()

        assert len(result) == 2
        assert isinstance(created1.id, uuid.UUID)
        assert isinstance(created2.id, uuid.UUID)

    def test_prevents_duplicate_insertion(self, test_db):
        job_id = uuid.uuid4()

        first_job = StatementImportJob(
            id=job_id,
            statement_source=StatementSource.REVOLUT,
            file_path="/path/to/statement.csv",
        )
        duplicate_job = StatementImportJob(
            id=job_id,
            statement_source=StatementSource.REVOLUT,
            file_path="/path/to/statement.csv",
        )

        create_new_job(new_job=first_job, db=test_db)

        with pytest.raises(DuplicateEntryError):
            create_new_job(new_job=duplicate_job, db=test_db)

        with Session(test_db) as session:
            jobs = session.exec(select(StatementImportJob)).all()

        assert len(jobs) == 1
        assert jobs[0].id == job_id


class TestLoadJob:
    def test_loads_existing_job(self, test_db):
        job = StatementImportJob(
            statement_source=StatementSource.REVOLUT,
            file_path="/path/to/statement.csv",
        )
        created = create_new_job(new_job=job, db=test_db)

        loaded = load_job(job_id=created.id, db=test_db)

        assert loaded is not None
        assert loaded.id == created.id
        assert loaded.statement_source == created.statement_source
        assert loaded.file_path == created.file_path

    def test_returns_none_when_not_found(self, test_db):
        non_existing_id = uuid.uuid4()
        loaded = load_job(job_id=non_existing_id, db=test_db)
        assert loaded is None


class TestUpdateJob:
    def test_updates_job_attributes_in_db(self, test_db):
        job = StatementImportJob(
            statement_source=StatementSource.REVOLUT,
            file_path="/path/to/statement.csv",
        )
        created = create_new_job(new_job=job, db=test_db)

        # Making updates to the created job
        new_timestamp = dt.datetime(2026, 2, 1, 12, 0, 0)
        created.status = ImportJobStatus.RUNNING
        created.failure_reason = "random"
        created.updated_at = new_timestamp
        created.completed_at = new_timestamp
        created.started_at = new_timestamp

        updated = update_job(updated_job=created, db=test_db)

        assert updated.status == ImportJobStatus.RUNNING
        assert updated.failure_reason == "random"
        assert updated.updated_at == new_timestamp
        assert updated.completed_at == new_timestamp
        assert updated.started_at == new_timestamp

        # Verify that values were persisted to the DB
        with Session(test_db) as session:
            stored = session.get(StatementImportJob, created.id)

        assert stored is not None
        assert stored.status == ImportJobStatus.RUNNING
        assert stored.failure_reason == "random"
        assert stored.updated_at == new_timestamp
        assert stored.completed_at == new_timestamp
        assert stored.started_at == new_timestamp

    def test_raises_exception_when_job_not_found(self, test_db):
        non_existing_job = StatementImportJob(
            id=uuid.uuid4(),
            statement_source=StatementSource.REVOLUT,
            file_path="/path/to/statement.csv",
        )

        with pytest.raises(ValueError, match="not found"):
            update_job(updated_job=non_existing_job, db=test_db)
