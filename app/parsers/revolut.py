import datetime as dt
import logging
from decimal import Decimal
from hashlib import sha256
from typing import Any, BinaryIO

import openpyxl
from pydantic import (
    BaseModel,
    ConfigDict,
    computed_field,
    Field,
    model_validator,
    ValidationError,
)

from app.project_types import ParsedTransaction, TransactionType, TxnSource, Side

logger = logging.getLogger(__name__)


def parse_revolut_statement(statement: BinaryIO) -> list[ParsedTransaction]:
    statement_rows = get_statement_rows(statement)
    normalized_trasactions = []
    rejected_count = 0
    for row in statement_rows:
        try:
            normalized_trasactions.append(RawTransactionRevolut.model_validate(row))
        except ValidationError:
            rejected_count += 1

    standardized_transactions = []
    for normalized in normalized_trasactions:
        standardized_transactions.append(normalized.to_parsed_transaction())

    logger.log(logging.INFO, "### Revolut Parser finished")
    logger.log(logging.INFO, f"Parsed valid transactions: {len(standardized_transactions)}")
    logger.log(logging.INFO, f"Rejected rows: {rejected_count}")

    return standardized_transactions


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

    transaction_datetime: dt.datetime = Field(alias="Started Date")
    counterparty: str = Field(alias="Description")
    raw_amount: Decimal = Field(alias="Amount")
    orig_currency: str = Field(alias="Currency")
    transaction_completed_datetime: dt.datetime = Field(alias="Completed Date")
    balance_after: Decimal = Field(alias="Balance")
    raw_txn_type: str = Field(alias="Type")
    product: str = Field(alias="Product")
    state: str = Field(alias="State")
    source: TxnSource = TxnSource.REVOLUT

    # 1. Calculated fields required by the program
    @computed_field
    @property
    def note(self) -> str | None:
        txn_note = None
        if self.raw_txn_type.upper() == "CARD REFUND":
            txn_note = f"Refund from {self.counterparty}"
        return txn_note

    @computed_field
    @property
    def orig_amount(self) -> Decimal:
        return abs(self.raw_amount)

    @computed_field
    @property
    def side(self) -> Side:
        return Side.DEBIT if self.raw_amount <= 0 else Side.CREDIT

    @computed_field
    @property
    def type(self) -> TransactionType:
        mapping = {
            "ATM": TransactionType.CASH_WITHDRAWAL,
            "Card Payment": TransactionType.CARD_PAYMENT,
            "Transfer": TransactionType.TRANSFER,
        }
        return mapping.get(self.raw_txn_type, TransactionType.OTHER)

    @computed_field
    @property
    def dedup_key(self) -> str:
        dedup_data = (
            # TODO: replace str(datetime) with datetime.isoformat(). Requires migrating existing PROD data
            f"{str(self.transaction_datetime).strip().lower()}_"
            f"{str(self.transaction_completed_datetime).strip().lower()}_"
            f"{str(self.counterparty).strip().lower()}_"
            f"{str(self.orig_amount).strip().lower()}_"
            f"{str(self.balance_after).strip().lower()}_"
        )

        hash_algo = sha256()
        hash_algo.update(dedup_data.encode())

        return hash_algo.hexdigest()

    # 2. Filtering out unsupported transactions
    @model_validator(mode="after")
    def is_valid_transaction(self) -> "RawTransactionRevolut":
        # Only use current account transactions (excl. saving, trading, etc.)
        if self.product.upper() != "CURRENT":
            raise ValueError(f"Only Current product is supported. Got: {self.product}")

        if self.state.upper() != "COMPLETED":
            raise ValueError(
                f"Only completed transactions supported. Got state: {self.state}"
            )

        if self.raw_txn_type.upper() in {
            "CASHBACK",
            "EXCHANGE",
            "TOPUP",
            "FEE",
            "TRADE",
        }:
            raise ValueError(f"Transaction type {self.raw_txn_type} is not supported")

        return self

    # Conversion to app domain model: ParsedTransaction
    def to_parsed_transaction(self) -> ParsedTransaction:
        return ParsedTransaction.model_validate(self.model_dump())
