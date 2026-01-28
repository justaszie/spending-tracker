import datetime as dt
import logging
from decimal import Decimal
from hashlib import sha256
from typing import Any, BinaryIO

import openpyxl
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
    ValidationError,
)

from app.project_types import ImportedTransaction, TransactionType, TxnSource, Side

logger = logging.getLogger(__name__)


def parse_revolut_statement(statement: BinaryIO) -> list[ImportedTransaction]:
    statement_rows = get_statement_rows(statement)
    transactions = []
    rejected_count = 0
    for row in statement_rows:
        try:
            transactions.append(RawTransactionRevolut.model_validate(row))
        except ValidationError:
            rejected_count += 1

    normalized = [convert_to_standardized_transaction(txn) for txn in transactions]

    logger.log(logging.INFO, "### Revolut Parser finished")
    logger.log(logging.INFO, f"Imported valid transactions: {len(normalized)}")
    logger.log(logging.INFO, f"Rejected rows: {rejected_count}")

    return normalized


def get_statement_rows(statement: BinaryIO) -> list[dict[str, Any]]:
    # read_only mode auto-closes the excel file
    workbook = openpyxl.load_workbook(statement, read_only=True)
    try:
        sheet = workbook.active
        if not sheet:
            return []

        rows_iterator = sheet.iter_rows(values_only=True)
        first_row = next(rows_iterator)
        headers = [str(header) for header in first_row]

        rows = [
            {header: value for header, value in zip(headers, row)}
            for row in rows_iterator
        ]
        return rows
    finally:
        workbook.close()


class RawTransactionRevolut(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    started_at: dt.datetime = Field(alias="Started Date")
    completed_at: dt.datetime = Field(alias="Completed Date")
    description: str = Field(alias="Description")
    amount: Decimal = Field(alias="Amount")
    currency: str = Field(alias="Currency")
    balance_after: Decimal = Field(alias="Balance")
    type: str = Field(alias="Type")
    account_type: str = Field(alias="Product")
    state: str = Field(alias="State")

    # Filtering out unsupported transactions
    @model_validator(mode="after")
    def is_valid_transaction(self) -> "RawTransactionRevolut":
        # Only use current account transactions (excl. saving, trading, etc.)
        if self.account_type.upper() != "CURRENT":
            raise ValueError(
                f"Only Current product is supported. Got: {self.account_type}"
            )

        if self.state.upper() != "COMPLETED":
            raise ValueError(
                f"Only completed transactions supported. Got state: {self.state}"
            )

        if self.type.upper() in {
            "CASHBACK",
            "EXCHANGE",
            "TOPUP",
            "FEE",
            "TRADE",
        }:
            raise ValueError(f"Transaction type {self.type} is not supported")

        return self


def convert_to_standardized_transaction(
    transaction: RawTransactionRevolut,
) -> ImportedTransaction:
    standardized = ImportedTransaction(
        transaction_datetime=transaction.started_at,
        type=get_transaction_type(transaction),
        counterparty=transaction.description,
        orig_amount=abs(transaction.amount),
        orig_currency=transaction.currency,
        side=get_side(transaction),
        note=get_note(transaction),
        source=TxnSource.REVOLUT,
        dedup_key=calculate_dedup_key(transaction),
    )

    return standardized


# 1. Calculated fields required by the program
def get_transaction_type(transaction: RawTransactionRevolut) -> TransactionType:
    mapping = {
        "ATM": TransactionType.CASH_WITHDRAWAL,
        "Card Payment": TransactionType.CARD_PAYMENT,
        "Transfer": TransactionType.TRANSFER,
    }
    return mapping.get(transaction.type, TransactionType.OTHER)


def get_note(transaction: RawTransactionRevolut) -> str | None:
    txn_note = None
    if transaction.type.upper() == "CARD REFUND":
        txn_note = f"Refund from {transaction.description}"
    return txn_note


def get_side(transaction: RawTransactionRevolut) -> Side:
    return Side.DEBIT if transaction.amount <= 0 else Side.CREDIT


def calculate_dedup_key(transaction: RawTransactionRevolut) -> str:
    dedup_data = (
        # TODO: replace str(datetime) with datetime.isoformat(). Requires migrating existing PROD data
        f"{str(transaction.started_at).strip().lower()}_"
        f"{str(transaction.completed_at).strip().lower()}_"
        f"{str(transaction.description).strip().lower()}_"
        f"{str(transaction.amount).strip().lower()}_"
        f"{str(transaction.balance_after).strip().lower()}_"
    )

    hash_algo = sha256()
    hash_algo.update(dedup_data.encode())

    return hash_algo.hexdigest()
