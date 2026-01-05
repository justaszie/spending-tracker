import datetime as dt
from typing import BinaryIO, Callable

import openpyxl

from app.transactions import Transaction
from app.project_types import Bank

ParserFN = Callable[[BinaryIO], list[Transaction]]

def get_parser(bank: Bank) -> ParserFN | None:
    if bank == 'revolut':
        return parse_revolut_statement

def parse_revolut_statement(file: BinaryIO) -> list[Transaction]:
    workbook = openpyxl.load_workbook(file)
    sheet = workbook.active
    rows = sheet.iter_rows(values_only=True)
    headers = next(rows)
    print(headers)
    return [Transaction(started_at=dt.datetime(2025, 12, 11), amount_cents=120, currency="EUR")]