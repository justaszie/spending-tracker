from collections.abc import Callable
from typing import BinaryIO

from app.project_types import ExtractedTransaction, StatementSource
import app.statement_extractors.revolut as revolut_extractor
import app.statement_extractors.swedbank as swedbank_extractor

ExtractorFN = Callable[[BinaryIO], list[ExtractedTransaction]]

# Registry of extractors
_registry: dict[StatementSource, ExtractorFN] = {
    StatementSource.REVOLUT: revolut_extractor.extract_transactions,
    StatementSource.SWEDBANK: swedbank_extractor.extract_transactions,
}


def get_extractor(statement_source: StatementSource) -> ExtractorFN | None:
    return _registry.get(statement_source)
