from typing import Self

from pydantic import (
    BaseModel,
    ConfigDict,
    field_validator,
    model_validator,
)

from app.core.config import app_config
from app.core.project_types import StatementSource
from app.statement_extractors.registry import (
    allowed_content_types,
    allowed_file_extensions,
)


class StatementMetadata(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    source: StatementSource
    file_name: str
    file_size: int
    file_type: str | None

    @field_validator("file_size")
    @classmethod
    def valid_file_size(cls, value: int):
        if value <= 0:
            raise ValueError("Statement file can't be empty")

        max_size = app_config.MAX_STATEMENT_SIZE
        if value > max_size:
            raise ValueError(
                f"Statement file can't exceed {max_size / 1024**2}MB. "
                f"Try splitting the statement file into smaller chunks"
            )
        return value

    @model_validator(mode="after")
    def is_valid_type(self) -> Self:
        allowed_extensions = allowed_file_extensions(self.source)

        # If file contains a supported extension, allow it
        file_name_parts = self.file_name.split(".")
        if file_name_parts:
            file_extension = file_name_parts[-1].lower()
            if file_extension in allowed_extensions:
                return self

        if self.file_type and (
            self.file_type.lower() in allowed_content_types(self.source)
            # Default content type is allowed since we can't predict what values clients can set
            or self.file_type.lower() == "application/octet-stream"
        ):
            return self

        raise ValueError(
            f"Statement file type is not valid for {self.source.value}. "
            f"Supported Types: {allowed_extensions}"
        )
