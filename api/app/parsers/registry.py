# Registry of parsers
from typing import BinaryIO, Callable

from app.parsers.revolut import parse_revolut_statement
from app.project_types import Bank, ParsedTransaction

ParserFN = Callable[[BinaryIO], list[ParsedTransaction]]

_registry: dict[Bank, ParserFN] = {
    "revolut": parse_revolut_statement,
    # "swedbank": ...,
}

def get_parser(bank: Bank) -> ParserFN | None:
    return _registry.get(bank)