from pydantic import ValidationError
import pytest

from app.core.project_types import StatementSource
from app.statement_validation import StatementMetadata


class TestRevolutFileTypeValidation:
    @pytest.fixture(scope="class")
    def valid_size(self):
        return int(0.5 * 1024**2)

    @pytest.mark.parametrize(
        "content_type",
        [
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/vnd.ms-excel",
            "application/octet-stream",
        ],
    )
    def test_allows_file_with_valid_type(self, valid_size, content_type):
        validated = StatementMetadata(
            source=StatementSource.REVOLUT,
            file_name="whatever",
            file_size=valid_size,
            file_type=content_type,
        )
        assert isinstance(validated, StatementMetadata)

    @pytest.mark.parametrize("file_extension", ["xlsx", "xls"])
    def test_allows_file_with_valid_extension(self, valid_size, file_extension):
        file_name = f"revolut_statement_2025-02-02.{file_extension}"
        validated = StatementMetadata(
            source=StatementSource.REVOLUT,
            file_name=file_name,
            file_size=valid_size,
            file_type="any/content-type",
        )
        assert isinstance(validated, StatementMetadata)

    @pytest.mark.parametrize(
        ("file_extension", "content_type"),
        [
            ("pdf", "application.pdf"),
            ("txt", "text/plain"),
            ("", "text/plain"),
            ("pdf", None),
        ],
    )
    def test_rejects_invalid_types(self, valid_size, file_extension, content_type):
        file_name = f"revolut_statement_2025-02-02.{file_extension}"
        with pytest.raises(ValidationError) as exc_info:
            StatementMetadata(
                source=StatementSource.REVOLUT,
                file_name=file_name,
                file_size=valid_size,
                file_type=content_type,
            )
        validation_exc = exc_info.value
        assert "file type is not valid" in validation_exc.errors()[0]["msg"]


class TestSwedbankFileTypeValidation:
    @pytest.fixture(scope="class")
    def valid_size(self):
        return int(0.5 * 1024**2)

    @pytest.mark.parametrize(
        "content_type",
        [
            "text/csv",
            "text/plain",
            "application/octet-stream",
        ],
    )
    def test_allows_file_with_valid_type(self, valid_size, content_type):
        validated = StatementMetadata(
            source=StatementSource.SWEDBANK,
            file_name="whatever",
            file_size=valid_size,
            file_type=content_type,
        )
        assert isinstance(validated, StatementMetadata)

    @pytest.mark.parametrize("file_extension", ["csv", "txt"])
    def test_allows_file_with_valid_extension(self, valid_size, file_extension):
        file_name = f"swedbank_statement_2025-02-02.{file_extension}"
        validated = StatementMetadata(
            source=StatementSource.SWEDBANK,
            file_name=file_name,
            file_size=valid_size,
            file_type="any/content-type",
        )
        assert isinstance(validated, StatementMetadata)

    @pytest.mark.parametrize(
        ("file_extension", "content_type"),
        [
            ("pdf", "application/pdf"),
            ("xlsx", "application/vnd.ms-excel"),
            ("", "application/pdf"),
            ("pdf", None),
        ],
    )
    def test_rejects_invalid_types(self, valid_size, file_extension, content_type):
        file_name = f"swedbank_statement_2025-02-02.{file_extension}"
        with pytest.raises(ValidationError) as exc_info:
            StatementMetadata(
                source=StatementSource.SWEDBANK,
                file_name=file_name,
                file_size=valid_size,
                file_type=content_type,
            )
        validation_exc = exc_info.value
        assert "file type is not valid" in validation_exc.errors()[0]["msg"]


class TestFileSizeValidation:
    @pytest.fixture(scope="class")
    def valid_file_type(self):
        return "application/octet-stream"

    @pytest.mark.parametrize("file_size", [1, int(0.5 * 1024**2), 2 * 1024**2 - 1])
    def test_allows_size_greater_than_zero_and_less_than_2mb(
        self, file_size, valid_file_type
    ):
        validated = StatementMetadata(
            source=StatementSource.REVOLUT,
            file_name="statement.xlsx",
            file_size=file_size,
            file_type=valid_file_type,
        )
        assert validated.file_size == file_size

    @pytest.mark.parametrize("file_size", [0, -1, -1024])
    def test_rejects_zero_or_negative_size(self, file_size, valid_file_type):
        with pytest.raises(ValidationError) as exc_info:
            StatementMetadata(
                source=StatementSource.REVOLUT,
                file_name="statement.xlsx",
                file_size=file_size,
                file_type=valid_file_type,
            )
        validation_exc = exc_info.value
        assert "can't be empty" in validation_exc.errors()[0]["msg"]

    def test_rejects_size_greater_than_2mb(self, valid_file_type):
        with pytest.raises(ValidationError) as exc_info:
            StatementMetadata(
                source=StatementSource.REVOLUT,
                file_name="statement.xlsx",
                file_size=2 * 1024**2 + 1,
                file_type=valid_file_type,
            )
        validation_exc = exc_info.value
        assert "can't exceed" in validation_exc.errors()[0]["msg"]
