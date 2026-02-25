from io import BytesIO
import uuid

import pytest

from app.core.project_types import StatementSource
from app.statement_validation import StatementMetadata
from app.storage.file_storage import FileStorage, StatementDownloadError

BUCKET_NAME = "test_statements"


@pytest.fixture
def supabase(mocker):
    return mocker.Mock()


@pytest.fixture
def supabase_with_bucket(mocker):
    supabase = mocker.Mock()
    mock_bucket = mocker.Mock()
    mock_bucket.id = BUCKET_NAME
    supabase.storage.list_buckets.return_value = [mock_bucket]

    return supabase


@pytest.fixture
def statement_meta():
    return StatementMetadata(
        source=StatementSource.REVOLUT,
        file_name="test_stmt.xlsx",
        file_size=(1 * 1024**2),
        file_type="application/octet-stream",
    )


TEST_USER_ID = uuid.UUID("0a2aafb1-473e-4dcd-b7d4-3f18ba388d4d")


class TestFileUpload:
    def test_uploads_statement_to_existing_bucket(
        self, mocker, supabase_with_bucket, statement_meta
    ):
        mock_timestamp = "2025-11-02T12:11:10"
        mocker.patch(
            "app.storage.file_storage.dt.datetime"
        ).now.return_value.isoformat.return_value = mock_timestamp

        expected = f"{TEST_USER_ID}/revolut/{mock_timestamp}_test_stmt.xlsx"
        upload_method = supabase_with_bucket.storage.from_.return_value.upload
        upload_method.return_value.path = expected

        create_bucket_method = supabase_with_bucket.storage.create_bucket

        storage = FileStorage(supabase_with_bucket)

        test_file_content = b"sample content 123"
        test_file = BytesIO(test_file_content)
        file_path = storage.upload_statement(
            user_id=TEST_USER_ID,
            file=test_file,
            statement_metadata=statement_meta,
            storage_bucket=BUCKET_NAME,
        )

        assert file_path == expected
        upload_method.assert_called_once_with(
            file=test_file_content,
            path=expected,
            file_options={"cache-control": "3600", "upsert": "true"},
        )
        create_bucket_method.assert_not_called()

    def test_creates_bucket_if_not_found(self, supabase, statement_meta):
        supabase.storage.list_buckets.return_value = []

        create_bucket_method = supabase.storage.create_bucket
        upload_method = supabase.storage.from_.return_value.upload

        storage = FileStorage(supabase)

        test_file_content = b"sample content 123"
        test_file = BytesIO(test_file_content)
        storage.upload_statement(
            user_id=TEST_USER_ID,
            file=test_file,
            statement_metadata=statement_meta,
            storage_bucket=BUCKET_NAME.capitalize(),  # testing that the name is normalized to lowercase
        )

        create_bucket_method.assert_called_once_with(
            BUCKET_NAME,
            options={
                "public": False,
            },
        )
        upload_method.assert_called()

    def test_rejects_empty_file(self, mocker, supabase_with_bucket, statement_meta):
        storage = FileStorage(supabase_with_bucket)

        empty_file = BytesIO(b"")
        with pytest.raises(ValueError):
            storage.upload_statement(
                user_id=TEST_USER_ID,
                file=empty_file,
                statement_metadata=statement_meta,
                storage_bucket=BUCKET_NAME,
            )


class TestFileDownload:
    def test_downloads_statement(self, supabase):
        test_data = b"sample 123"
        supabase.storage.from_.return_value.download.return_value = test_data

        storage = FileStorage(supabase)
        result = storage.load_file(filepath="random", bucket=BUCKET_NAME)

        # load_file returns bytes data wrapped in BytesIO
        assert result.read() == test_data

    def test_maps_exceptions_to_standard(self, supabase):
        supabase.storage.from_.return_value.download.side_effect = ValueError(
            "Some Error"
        )

        storage = FileStorage(supabase)
        with pytest.raises(StatementDownloadError):
            storage.load_file(filepath="random", bucket=BUCKET_NAME)
