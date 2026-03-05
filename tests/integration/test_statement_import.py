from io import BytesIO
from pathlib import Path
from typing import BinaryIO
import datetime as dt
import uuid

from fastapi.testclient import TestClient
from httpx import Response
from sqlmodel import Session, select
import pytest

from app.core.config import app_config
from app.core.dependencies import (
    get_authenticated_user,
    get_db_engine,
    get_file_storage,
)
from app.core.project_types import ImportJobStatus
from app.db.statement_import_jobs import load_job
from app.db.transactions import Transaction
from app.main import app
from app.statement_validation import StatementMetadata
from app.storage.file_storage import StatementDownloadError

TEST_USER_ID = uuid.UUID("e92460b8-c69a-4706-bf9c-addefd582836")


IMPORT_API_PATH = f"{app_config.V1_API_PREFIX}/statement-imports"


@pytest.fixture
def test_client(test_db):
    app.dependency_overrides[get_file_storage] = lambda: FakeStorage()
    app.dependency_overrides[get_authenticated_user] = lambda: TEST_USER_ID
    app.dependency_overrides[get_db_engine] = lambda: test_db

    with TestClient(app) as client:
        try:
            yield client
        finally:
            app.dependency_overrides.clear()


class FakeStorage:
    def __init__(self):
        self.stored_data = {}

    def upload_statement(
        self,
        user_id: uuid.UUID,
        file: BinaryIO,
        statement_metadata: StatementMetadata,
        storage_bucket: str,
    ) -> str:
        _ = storage_bucket
        timestamp = dt.datetime.now().isoformat()
        file_path = (
            f"{user_id}/{statement_metadata.source.value}/"
            f"{timestamp}_{statement_metadata.file_name}"
        )
        file_data: bytes = file.read()
        if not file_data:
            raise ValueError("No content in the file provided")

        # Store the statement data in-memory
        self.stored_data[file_path] = file_data

        return file_path

    def load_file(
        self,
        filepath: str,
        bucket: str,
    ) -> BytesIO:
        _ = bucket
        try:
            return BytesIO(self.stored_data[filepath])
        except Exception as e:
            raise StatementDownloadError(f"Failed to download statement: {e}") from e


def get_transactions_for_job(job_id: uuid.UUID, engine) -> list[Transaction]:
    with Session(engine) as session:
        statement = select(Transaction).where(Transaction.import_job_id == job_id)
        result = session.exec(statement).all()
        return list(result)


def import_statement(
    statement_filename: str,
    test_client: TestClient,
    statement_source: str,
) -> Response:
    statement_path = Path(__file__).parent.resolve() / statement_filename
    with Path.open(statement_path, "rb") as statement_file:
        return test_client.post(
            IMPORT_API_PATH,
            data={"statement_source": statement_source},
            files={"statement_file": (statement_filename, statement_file)},
        )


class TestImportRevolut:
    def test_imports_revolut_statement(self, test_client, test_db):
        statement_filename = "test_revolut_full.xlsx"
        response = import_statement(statement_filename, test_client, "revolut")

        body = response.json()
        import_job_id = uuid.UUID(body["import_job_id"])
        import_job_status = body["import_job_status"]

        # Verifying the API response is correct
        assert response.status_code == 202
        assert import_job_status == "pending"

        # TestClient.post() only returns when background tasks are completed
        # So here we can assert that the job is completed.
        completed_job = load_job(import_job_id, test_db)
        assert completed_job is not None
        assert completed_job.status == ImportJobStatus.COMPLETED

        imported_txn_count = completed_job.imported_txn_count or 0
        duplicate_txn_count = completed_job.duplicate_txn_count or 0

        assert imported_txn_count == 16
        assert duplicate_txn_count == 0

        # Fetch all transactions for this job and verify that their count matches imported_txn_count.
        transactions_for_job = get_transactions_for_job(import_job_id, test_db)
        assert len(transactions_for_job) == imported_txn_count

        # Sanity check that category enrichment ran: at least some transactions have a spending_category
        with_category = sum(
            1 for t in transactions_for_job if t.spending_category is not None
        )
        assert with_category >= 2, (
            "expected at least a few transactions to have spending_category set"
        )

    def test_does_not_import_duplicates(self, test_client, test_db):
        """Import 2 overlapping statements and verify that duplicate transactions are not inserted"""
        statement_filename = "test_revolut_subset.xlsx"
        response = import_statement(statement_filename, test_client, "revolut")
        body = response.json()

        import_job_id = uuid.UUID(body["import_job_id"])
        completed_job = load_job(import_job_id, test_db)
        assert completed_job is not None
        assert completed_job.status == ImportJobStatus.COMPLETED

        # Verify that the first transactions were inserted
        transactions = get_transactions_for_job(completed_job.id, test_db)
        assert len(transactions) == 2

        # Import overlapping statement
        statement_filename = "test_revolut_full.xlsx"
        response = import_statement(statement_filename, test_client, "revolut")
        body = response.json()

        import_job_id = uuid.UUID(body["import_job_id"])
        completed_job = load_job(import_job_id, test_db)
        assert completed_job is not None
        assert completed_job.status == ImportJobStatus.COMPLETED

        # Verify that duplicate transactions were not inserted
        assert completed_job.imported_txn_count == 14
        assert completed_job.duplicate_txn_count == 2

        transactions = get_transactions_for_job(completed_job.id, test_db)
        assert len(transactions) == completed_job.imported_txn_count


class TestRequestValidation:
    def test_rejects_invalid_file_type(self, test_client):
        # Upload a file with an unsupported extension/content type
        files = {
            "statement_file": (
                "invalid.csv",
                BytesIO(b"not a valid statement"),
                "text/plain",
            )
        }

        response = test_client.post(
            IMPORT_API_PATH,
            data={"statement_source": "revolut"},
            files=files,
        )

        assert response.status_code == 422

    def test_rejects_too_large_file(self, test_client):
        # Build a payload that's just over the configured max size
        too_large_size = app_config.MAX_STATEMENT_SIZE + 1
        payload = b"x" * too_large_size

        files = {
            "statement_file": (
                "large_statement.csv",
                BytesIO(payload),
                "application/octet-stream",
            )
        }

        response = test_client.post(
            IMPORT_API_PATH,
            data={"statement_source": "swedbank"},
            files=files,
        )

        assert response.status_code == 422

    def test_rejects_unknown_source(self, test_client):
        files = {
            "statement_file": (
                "large_statement.csv",
                BytesIO(b"abc"),
                "application/octet-stream",
            )
        }

        response = test_client.post(
            IMPORT_API_PATH,
            data={"statement_source": "unknown_bank"},
            files=files,
        )

        assert response.status_code == 422


class TestImportSwedbank:
    def test_imports_swedbank_statement(self, test_client, test_db):
        statement_filename = "test_swedbank_full.csv"
        response = import_statement(
            statement_filename, test_client, statement_source="swedbank"
        )

        body = response.json()
        import_job_id = uuid.UUID(body["import_job_id"])
        import_job_status = body["import_job_status"]

        assert response.status_code == 202
        assert import_job_status == "pending"

        completed_job = load_job(import_job_id, test_db)
        assert completed_job is not None
        assert completed_job.status == ImportJobStatus.COMPLETED

        imported_txn_count = completed_job.imported_txn_count or 0
        duplicate_txn_count = completed_job.duplicate_txn_count or 0

        assert imported_txn_count == 6
        assert duplicate_txn_count == 0

        transactions_for_job = get_transactions_for_job(import_job_id, test_db)
        assert len(transactions_for_job) == imported_txn_count

        with_category = sum(
            1 for t in transactions_for_job if t.spending_category is not None
        )
        assert with_category >= 1, (
            "expected at least one transactions to have spending_category set"
        )

    def test_does_not_import_duplicates(self, test_client, test_db):
        """Import 2 overlapping statements and verify that duplicate transactions are not inserted"""
        statement_filename = "test_swedbank_subset.csv"
        response = import_statement(
            statement_filename, test_client, statement_source="swedbank"
        )
        body = response.json()

        import_job_id = uuid.UUID(body["import_job_id"])
        completed_job = load_job(import_job_id, test_db)
        assert completed_job is not None
        assert completed_job.status == ImportJobStatus.COMPLETED

        transactions = get_transactions_for_job(completed_job.id, test_db)
        assert len(transactions) == 1

        statement_filename = "test_swedbank_full.csv"
        response = import_statement(
            statement_filename, test_client, statement_source="swedbank"
        )
        body = response.json()

        import_job_id = uuid.UUID(body["import_job_id"])
        completed_job = load_job(import_job_id, test_db)
        assert completed_job is not None
        assert completed_job.status == ImportJobStatus.COMPLETED

        assert completed_job.imported_txn_count == 5
        assert completed_job.duplicate_txn_count == 1
        transactions = get_transactions_for_job(completed_job.id, test_db)
        assert len(transactions) == (completed_job.imported_txn_count or 0)
