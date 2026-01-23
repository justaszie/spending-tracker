from enum import StrEnum
from uuid import UUID

import datetime as dt
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class StatementSource(StrEnum):
    SWEDBANK = "swedbank"
    REVOLUT = "revolut"


class JobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"


class Side(StrEnum):
    DEBIT = "Debit"
    CREDIT = "Credit"


class TxnSource(StrEnum):
    CASH = "Cash"
    SWEDBANK = "Swedbank"
    REVOLUT = "Revolut"


class ParsedTransaction(BaseModel):
    transaction_datetime: dt.datetime
    counterparty: str
    orig_amount: Decimal
    orig_currency: str
    side: Side
    source: TxnSource
    note: str | None = None
    dedup_key: str
