# Integrate with supabase file storage
import datetime as dt
import os
from io import BytesIO
from typing import Any, BinaryIO, TextIO
from uuid import UUID

from .project_types import Bank


class FileStorage:
    def __init__(self, storage_client: Any):
        self._storage_client = storage_client

    def upload_statement(
        self, user_id: UUID, job_id: UUID, bank: Bank, filename: str, file: BinaryIO
    ) -> str:
        bucket: str = os.environ.get("STATEMENTS_BUCKET")
        timestamp = dt.datetime.now().isoformat()
        file_path = f"{user_id}/{bank}/{timestamp}_{filename}"

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
        bucket: str = os.environ.get("STATEMENTS_BUCKET"),
    ) -> BytesIO:
        response = (
            self._storage_client.storage
            .from_(bucket)
            .download(filepath)
        )
        return BytesIO(response)
