from typing import BinaryIO, Callable

from app.parsers.revolut import parse_revolut_statement
from app.parsers.swedbank import parse_swedbank_statement
from app.project_types import StatementSource, ParsedTransaction

ParserFN = Callable[[BinaryIO], list[ParsedTransaction]]

# Registry of parsers
_registry: dict[StatementSource, ParserFN] = {
    StatementSource.REVOLUT: parse_revolut_statement,
    StatementSource.SWEDBANK: parse_swedbank_statement,
}


def get_parser(statement_source: StatementSource) -> ParserFN | None:
    return _registry.get(statement_source)
