from decimal import Decimal
from enum import StrEnum
import datetime as dt

from pydantic import BaseModel


class StatementSource(StrEnum):
    SWEDBANK = "swedbank"
    REVOLUT = "revolut"


class JobStatus(StrEnum):
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
