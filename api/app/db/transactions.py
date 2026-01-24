import uuid
import datetime as dt
from decimal import Decimal

from sqlalchemy import Engine
from sqlmodel import Field, select, Session, SQLModel

from app.project_types import Side, TxnSource


class Transaction(SQLModel, table=True):
    __tablename__ = "transactions"

    id: uuid.UUID = Field(primary_key=True, default_factory=uuid.uuid4)
    transaction_datetime: dt.datetime = Field(nullable=False)
    counterparty: str = Field(nullable=False)
    orig_amount: Decimal = Field(nullable=False)
    orig_currency: str = Field(nullable=False)
    side: Side = Field(nullable=False)
    source: TxnSource = Field(nullable=False)
    eur_amount: Decimal = Field(nullable=False)
    manually_added: bool = Field(nullable=False, default=True)
    note: str | None = Field(default=None)
    category: str | None = Field(default=None)
    sub_category: str | None = Field(default=None)
    detail: str | None = Field(default=None)
    meal_type: str | None = Field(default=None)
    refunded_eur_amount: Decimal = Field(nullable=False, default=Decimal("0"))
    dedup_key: str = Field(nullable=False, unique=True)
    job_id: uuid.UUID = Field(nullable=True, default=None, foreign_key="jobs.id")
    user_id: uuid.UUID = Field(nullable=False)


def insert_transactions(transactions: list[Transaction], db: Engine) -> None:
    with Session(db) as session:
        session.add_all(transactions)
        session.commit()


def get_existing_dedup_keys(db: Engine) -> list[str]:
    with Session(db) as session:
        result = session.exec(select(Transaction.dedup_key)).all()
        return list(result)
