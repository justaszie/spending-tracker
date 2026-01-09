from enum import Enum
from typing import Literal
from uuid import UUID

import datetime as dt
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

type Bank = Literal["swedbank", "revolut"]
type JobStatus = Literal["pending", "complete"]

class Side(Enum):
    DEBIT = "Debit"
    CREDIT = "Credit"


class TxnSource(Enum):
    CASH = "Cash"
    SWEDBANK = "Swedbank"
    REVOLUT = "Revolut"


class ParsedTransaction(BaseModel):
    transaction_date: dt.datetime
    counterparty: str
    orig_amount: Decimal
    orig_currency: str
    side: "Side"
    source: "TxnSource"
    note: str | None = None

    model_config = ConfigDict(use_enum_values=True)


class Transaction(BaseModel):
    date: dt.datetime
    counterparty: str
    orig_amount: Decimal
    orig_currency: str
    side: Side
    source: TxnSource
    eur_amount: Decimal
    auto_added: bool
    note: str
    category: str
    sub_category: str
    detail: str
    meal_type: str
    dedup_hash: str