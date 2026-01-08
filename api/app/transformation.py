import datetime as dt
from decimal import Decimal
from enum import Enum
from uuid import UUID

from pydantic import BaseModel
from app.parsers.revolut import ParsedTransaction

# TODO: Consider moving the models and enums to some central file because there's reuse now
class Side(Enum):
    DEBIT = "Debit"
    CREDIT = "Credit"

# TODO: merge with "Bank" type in project_types ?
class TxnSource(Enum):
    CASH = "Cash"
    SWEDBANK = "Swedbank"
    REVOLUT = "Revolut"

class Transaction(BaseModel):
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

def enhance_transactions(tansactions: list[ParsedTransaction]) -> list[Transaction]:
    return []