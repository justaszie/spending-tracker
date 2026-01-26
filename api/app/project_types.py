import datetime as dt
from decimal import Decimal
from enum import StrEnum

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


class TxnSource(StrEnum):
    CASH = "cash"
    SWEDBANK = "swedbank"
    REVOLUT = "revolut"


class TransactionType(StrEnum):
    CARD_PAYMENT = "card_payment"
    CASH_WITHDRAWAL = "cash_withdrawal"
    TRANSFER = "transfer"
    OTHER = "other"


class ParsedTransaction(BaseModel):
    transaction_datetime: dt.datetime
    type: TransactionType
    counterparty: str
    orig_amount: Decimal
    orig_currency: str
    side: Side
    source: TxnSource
    note: str | None = None
    dedup_key: str
