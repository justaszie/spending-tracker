from io import BytesIO
from typing import Any, BinaryIO
from uuid import UUID
import datetime as dt
import logging

from app.statement_validation import StatementMetadata


class StatementDownloadError(Exception):
    pass


logger = logging.getLogger(__name__)


# Integrate with supabase file storage
class FileStorage:
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
        return response.path

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
