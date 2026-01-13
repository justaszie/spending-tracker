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


# class Transaction(BaseModel):
#     transaction_datetime: dt.datetime
#     counterparty: str
#     orig_amount: Decimal
#     orig_currency: str
#     side: Side
#     source: TxnSource
#     auto_added: bool = True
#     eur_amount: Decimal | None = None
#     note: str | None = None
#     category: str | None = None
#     sub_category: str | None = None
#     detail: str | None = None
#     meal_type: str | None = None
#     dedup_key: str
#     job_id: UUID

