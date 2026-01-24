import datetime as dt
from io import BytesIO
from typing import Any, BinaryIO
from uuid import UUID

from app.project_types import StatementSource


# Integrate with supabase file storage
class FileStorage:
    def __init__(self, storage_client: Any):
        self._storage_client = storage_client

    # Make this more generic. The caller will provide the specific bucket and file_path
    def upload_statement(
        self,
        statement_source: StatementSource,
        filename: str,
        file: BinaryIO,
        bucket: str,
        user_id: UUID
    ) -> str:
        timestamp = dt.datetime.now().isoformat()
        file_path = f"{user_id}/{statement_source.value}/{timestamp}_{filename}"

        file_data: bytes = file.read()
        if not file_data:
            raise ValueError("No content in the file provided")

        response = self._storage_client.storage.from_(bucket).upload(
            file=file_data,
            path=file_path,
            file_options={"cache-control": "3600", "upsert": "true"},
        )
        return response.path

    # Load a file from a bucket in supabase (download)
    def load_file(
        self,
        filepath: str,
        bucket: str,
    ) -> BytesIO:
        response = self._storage_client.storage.from_(bucket).download(filepath)
        return BytesIO(response)
