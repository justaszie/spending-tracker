import datetime as dt
import logging
from io import BytesIO
from pathlib import Path
from typing import Any, BinaryIO, Protocol, cast
from uuid import UUID

from app.statement_validation import StatementMetadata


class StatementDownloadError(Exception):
    pass


logger = logging.getLogger(__name__)


class StorageBackend(Protocol):
    def upload_statement(
        self,
        user_id: UUID,
        file: BinaryIO,
        statement_metadata: StatementMetadata,
        storage_bucket: str,
    ) -> str: ...

    def load_file(
        self,
        filepath: str,
        bucket: str,
    ) -> BytesIO: ...


# Integrate with supabase file storage
class SupabaseFileStorage:
    def __init__(self, supabase_client: Any):
        self._supabase_client = supabase_client

    def upload_statement(
        self,
        user_id: UUID,
        file: BinaryIO,
        statement_metadata: StatementMetadata,
        storage_bucket: str,
    ) -> str:
        timestamp = dt.datetime.now().isoformat()
        file_path = (
            f"{user_id}/{statement_metadata.source.value}/"
            f"{timestamp}_{statement_metadata.file_name}"
        )

        file_data: bytes = file.read()
        if not file_data:
            raise ValueError("No content in the file provided")

        storage_bucket = storage_bucket.strip().lower()
        # If the bucket doesn't exist yet, create it
        existing_buckets = self._supabase_client.storage.list_buckets()
        if storage_bucket not in {bucket.id.lower() for bucket in existing_buckets}:
            response = self._supabase_client.storage.create_bucket(
                storage_bucket,
                options={
                    "public": False,
                },
            )
            logger.info(f"Storage bucket created: {storage_bucket}")

        response = self._supabase_client.storage.from_(storage_bucket).upload(
            file=file_data,
            path=file_path,
            file_options={"cache-control": "3600", "upsert": "true"},
        )
        return cast(str, response.path)

    # Download a file from a storage bucket in supabase
    def load_file(
        self,
        filepath: str,
        bucket: str,
    ) -> BytesIO:
        try:
            response = self._supabase_client.storage.from_(bucket).download(filepath)
            return BytesIO(response)
        except Exception as e:
            raise StatementDownloadError(f"Failed to download statement: {e}") from e


class LocalFileStorage:
    def __init__(self, root: Path | str):
        self._root = Path(root)

    def upload_statement(
        self,
        user_id: UUID,
        file: BinaryIO,
        statement_metadata: StatementMetadata,
        storage_bucket: str,
    ) -> str:
        timestamp = dt.datetime.now().isoformat()
        relative_path = (
            f"{user_id}/{statement_metadata.source.value}/"
            f"{timestamp}_{statement_metadata.file_name}"
        )

        file_data: bytes = file.read()
        if not file_data:
            raise ValueError("No content in the file provided")

        storage_bucket = storage_bucket.strip().lower()
        full_path = self._root / storage_bucket / relative_path
        full_path.parent.mkdir(parents=True, exist_ok=True)

        full_path.write_bytes(file_data)
        logger.info("Stored statement locally at %s", full_path)

        return relative_path

    def load_file(
        self,
        filepath: str,
        bucket: str,
    ) -> BytesIO:
        storage_bucket = bucket.strip().lower()
        full_path = self._root / storage_bucket / filepath
        try:
            data = full_path.read_bytes()
            return BytesIO(data)
        except FileNotFoundError as e:
            raise StatementDownloadError(
                f"Failed to download statement from local storage: {e}"
            ) from e


# Backwards-compatible alias for existing imports and tests
FileStorage = SupabaseFileStorage
