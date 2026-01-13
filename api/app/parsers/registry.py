# Registry of parsers
from typing import BinaryIO, Callable

from app.parsers.revolut import parse_revolut_statement
from app.project_types import StatementSource, ParsedTransaction

ParserFN = Callable[[BinaryIO], list[ParsedTransaction]]

_registry: dict[StatementSource, ParserFN] = {
    "revolut": parse_revolut_statement,
    # "swedbank": ...,
}

def get_parser(statement_source: StatementSource) -> ParserFN | None:
    return _registry.get(statement_source)