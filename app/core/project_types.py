from decimal import Decimal
from enum import StrEnum
from typing import Self
import datetime as dt

from pydantic import BaseModel, model_validator


class StatementSource(StrEnum):
    SWEDBANK = "swedbank"
    REVOLUT = "revolut"


class ImportJobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Side(StrEnum):
    DEBIT = "debit"
    CREDIT = "credit"


class TransactionSource(StrEnum):
    MANUAL = "manual"
    SWEDBANK = "swedbank"
    REVOLUT = "revolut"


class TransactionType(StrEnum):
    CARD_PAYMENT = "card_payment"
    CASH_WITHDRAWAL = "cash_withdrawal"
    CASH_PAYMENT = "cash_payment"
    TRANSFER = "transfer"
    CARD_REFUND = "card_refund"
    OTHER = "other"


class ExtractedTransaction(BaseModel):
    transaction_datetime: dt.datetime
    type: TransactionType
    counterparty: str
    orig_amount: Decimal
    orig_currency: str
    side: Side
    source: TransactionSource
    note: str | None = None
    dedup_key: str


class ImportableTransaction(ExtractedTransaction):
    # Standardized currency amount is mandatory
    eur_amount: Decimal

    # Optional business data
    spending_category: str | None = None
    meal_type: str | None = None

    @model_validator(mode="after")
    def standardize_amounts_format(self) -> Self:
        self.orig_amount = self.orig_amount.quantize(Decimal("0.01"))
        self.eur_amount = self.eur_amount.quantize(Decimal("0.01"))
        return self
