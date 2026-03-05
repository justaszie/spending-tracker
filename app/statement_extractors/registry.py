from collections.abc import Callable, Collection
from typing import BinaryIO, TypedDict

from app.core.project_types import ExtractedTransaction, StatementSource
import app.statement_extractors.revolut as revolut_extractor
import app.statement_extractors.swedbank as swedbank_extractor

ExtractorFN = Callable[[BinaryIO], list[ExtractedTransaction]]


class ExtractorConfig(TypedDict):
    extractor_fn: ExtractorFN
    allowed_extensions: set[str]
    allowed_content_types: set[str]


# Registry of extractors
_registry: dict[StatementSource, ExtractorConfig] = {
    StatementSource.REVOLUT: {
        "extractor_fn": revolut_extractor.extract_transactions,
        "allowed_extensions": {"xlsx", "xls"},
        "allowed_content_types": {
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/vnd.ms-excel",
        },
    },
    StatementSource.SWEDBANK: {
        "extractor_fn": swedbank_extractor.extract_transactions,
        "allowed_extensions": {"csv", "txt"},
        "allowed_content_types": {"text/csv", "text/plain"},
    },
}


def get_extractor_config(statement_source: StatementSource) -> ExtractorConfig | None:
    return _registry.get(statement_source)


def get_extractor_fn(statement_source: StatementSource) -> ExtractorFN | None:
    extractor_config = _registry.get(statement_source)
    if extractor_config is None:
        return None

    return extractor_config.get("extractor_fn")


def allowed_file_extensions(statement_source: StatementSource) -> set[str]:
    config = get_extractor_config(statement_source)
    if config is None:
        return set()
    return config.get("allowed_extensions", set())


def allowed_content_types(statement_source: StatementSource) -> set[str]:
    config = get_extractor_config(statement_source)
    if config is None:
        return set()
    return config.get("allowed_content_types", set())
