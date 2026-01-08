### TODO: This should be core parsers logic - not revolut specific ###


import datetime as dt
from decimal import Decimal
from enum import Enum
from typing import Any, BinaryIO, Callable
from uuid import UUID

import openpyxl
from pydantic import BaseModel

from app.transactions import ParsedTransaction
from app.project_types import Bank


class Side(Enum):
    DEBIT = 'Debit'
    CREDIT = 'Credit'

class TxnSource(Enum):
    CASH = "Cash"
    SWEDBANK = "Swedbank"
    REVOLUT = "Revolut"

#TODO: Convert to base model for automated validation
# allow extras so that we can add non-validate fields like dedup_hash
# Purpose of this model should be make sure that extracted and cleaned transaction fits the expected model. I.e. parser done its job properly
# the model does not expect any enhancments like dedup hash at this point. This is just orchestrator <--> Parser boundary
class ParsedTransaction(BaseModel):
    date: dt.datetime
    counterparty: str
    orig_amount: Decimal
    orig_currency: str
    side: Side
    source: TxnSource
    eur_amount: Decimal
    transaction_id: UUID
    auto_added: bool
    note: str
    category: str
    sub_category: str
    detail: str
    meal_type: str
    dedup_hash: str

ParserFN = Callable[[BinaryIO], list[ParsedTransaction]]

def get_parser(bank: Bank) -> ParserFN | None:
    if bank == 'revolut':
        return parse_revolut_statement

def get_raw_transactions(statement: BinaryIO) -> list[dict[str, Any]]:
    #read_only mode auto-closes the excel file
    workbook = openpyxl.load_workbook(statement, read_only=True)
    try:
        sheet = workbook.active
        if not sheet:
            #TODO: Log that couldn't get the sheet
            return []

        rows = sheet.iter_rows(values_only=True)
        headers = next(rows)

        #TODO: Edge cases: empty rows, then non-empy rows after empty ones, etc.
        raw_txns = [
            {header: value for header, value in zip(headers, row)}
            for row in rows
        ]
        return raw_txns
    finally:
        workbook.close()


def filter_raw_transactions(raw_txns: list[dict[str, Any]]) -> list[dict[str, Any]]:
    pass


def clean_raw_transactions(raw_txns: list[dict[str, Any]]) -> list[dict[str, Any]]:
    pass


def parse_revolut_statement(statement: BinaryIO) -> list[ParsedTransaction]:
    raw_txns = get_raw_transactions(statement)

    filtered = filter_raw_transactions(raw_txns)
    clean_txns = clean_raw_transactions(filtered)

    return [Transactions[]]