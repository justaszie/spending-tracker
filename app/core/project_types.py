import datetime as dt
from decimal import Decimal
from enum import StrEnum
from typing import Literal, Self

from pydantic import BaseModel, Field, model_validator


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


type TransactionsSortField = Literal[
    "transaction_datetime",
    "counterparty",
    "spending_category",
    "side",
    "eur_amount",
]


class PeriodPreset(StrEnum):
    LAST_30 = "L30"
    MONTH_TO_DATE = "MTD"
    YEAR_TO_DATE = "YTD"
    ALL_TIME = "ALL_TIME"
    CUSTOM = "CUSTOM"

class MetricsGroupName(StrEnum):
    SPEND = "spend"

class DeltaValues(BaseModel):
    abs_change: Decimal
    # Important: the values are percentages, not ratios.
    # The pct_change can be null if previous value is 0
    pct_change: Decimal | None


class DeltasGroup(BaseModel):
    total: DeltaValues
    avg_daily: DeltaValues


class CategoryAggregate(BaseModel):
    category: str | None
    total: Decimal
    avg_daily: Decimal | None = None
    # Can be extended to add other by-category aggregate metrics.


class MetricsGroup(BaseModel):
    total: Decimal
    avg_daily: Decimal
    by_category: list[CategoryAggregate] = Field(default_factory=list)


class PeriodStats(BaseModel):
    date_from: dt.date
    date_to: dt.date
    days_count: int = Field(ge=1)
    groups: dict[MetricsGroupName, MetricsGroup] = Field(default_factory=dict)


class StatsDeltas(BaseModel):
    groups: dict[MetricsGroupName, DeltasGroup]


