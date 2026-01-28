import datetime as dt
import logging
import re
from csv import DictReader
from decimal import Decimal
from io import TextIOWrapper
from hashlib import sha256
from typing import Any, BinaryIO

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)

from app.project_types import ImportedTransaction, TransactionType, TransactionSource, Side

logger = logging.getLogger(__name__)

EXCL_DESCRIPTION_PATTERNS = (
    r"^apyvarta$",
    r"^likutis .*$",
)


def parse_swedbank_statement(statement: BinaryIO) -> list[ImportedTransaction]:
    statement_rows = get_statement_rows(statement)
    transactions = []
    rejected_count = 0
    for row in statement_rows:
        try:
            transactions.append(RawTransactionSwedbank.model_validate(row))
        except ValidationError:
            rejected_count += 1

    normalized = [convert_to_standardized_transaction(txn) for txn in transactions]

    logger.log(logging.INFO, "### Swedbank Parser finished")
    logger.log(logging.INFO, f"Imported valid transactions: {len(normalized)}")
    logger.log(logging.INFO, f"Rejected rows: {rejected_count}")

    return normalized


def get_statement_rows(statement: BinaryIO) -> list[dict[str, Any]]:
    # Input: csv file data
    # Output: list of dictionaries (mapping each column to value) - 1 for each row in csv
    text_reader = TextIOWrapper(statement)
    dict_reader = DictReader(text_reader)
    return [txn_as_dict for txn_as_dict in dict_reader]


class RawTransactionSwedbank(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    started_at: dt.datetime = Field(alias="Data")
    counterparty: str = Field(alias="Gavėjas")
    amount: Decimal = Field(alias="Suma")
    currency: str = Field(alias="Valiuta")
    description: str = Field(alias="Paaiškinimai")
    unique_id: str = Field(alias="Įrašo Nr.")
    type: str = Field(alias="Kodas")
    side: str = Field(alias="D/K")

    @field_validator("side")
    @classmethod
    def debit_or_credit(cls, value: str) -> str:
        if value.upper() not in {"D", "K"}:
            raise ValueError(f"Invalid Debit/Credit value: {value}")

        return value

    @model_validator(mode="after")
    def is_valid_transaction(self) -> "RawTransactionSwedbank":
        # Exclude entries such as total amount spent during period.
        # Such transactions contain patterns like "apyvarta..." in description field
        for pattern in EXCL_DESCRIPTION_PATTERNS:
            if re.search(pattern, self.description, re.IGNORECASE) is not None:
                raise ValueError(
                    f"Description {self.description} contains excluded pattern: {pattern}"
                )

        return self


def calculate_dedup_key(transaction: RawTransactionSwedbank) -> str:
    dedup_data = str(transaction.unique_id).strip().lower()

    hash_algo = sha256()
    hash_algo.update(dedup_data.encode())

    return hash_algo.hexdigest()


def get_counterparty(transaction: RawTransactionSwedbank) -> str:
    return transaction.counterparty or transaction.description


def get_transaction_type(transaction: RawTransactionSwedbank) -> TransactionType:
    # Cash withdrawals are marked as card payments with specific keyword in "Paaiskinimai" column
    if transaction.type == "K" and "grynieji" in transaction.description:
        return TransactionType.CASH_WITHDRAWAL

    mapping = {
        "K": TransactionType.CARD_PAYMENT,
        "MK": TransactionType.TRANSFER,
    }
    return mapping.get(transaction.type, TransactionType.OTHER)


def get_side(transaction: RawTransactionSwedbank) -> Side:
    return Side.DEBIT if transaction.side == "D" else Side.CREDIT


def convert_to_standardized_transaction(
    transaction: RawTransactionSwedbank,
) -> ImportedTransaction:
    standardized = ImportedTransaction(
        transaction_datetime=transaction.started_at,
        type=get_transaction_type(transaction),
        counterparty=get_counterparty(transaction),
        orig_amount=abs(transaction.amount),
        orig_currency=transaction.currency,
        side=get_side(transaction),
        note=transaction.description,
        source=TransactionSource.SWEDBANK,
        dedup_key=calculate_dedup_key(transaction),
    )
    return standardized
