import uuid
import datetime as dt
from decimal import Decimal

from sqlalchemy import Engine
from sqlmodel import Field, select, Session, SQLModel

from app.project_types import Side, TxnSource

class Transaction(SQLModel, table=True):
    __tablename__ = "transactions"

    # TODO: Consider job_id FK to link txns to job that inserted them
    id: uuid.UUID = Field(primary_key=True, default_factory=uuid.uuid4)
    transaction_datetime: dt.datetime = Field(nullable=False)
    counterparty: str = Field(nullable=False)
    orig_amount: Decimal = Field(nullable=False)
    orig_currency: str = Field(nullable=False)
    side: Side = Field(nullable=False)
    source: TxnSource = Field(nullable=False)
    eur_amount: Decimal = Field(nullable=False)
    auto_added: bool = Field(nullable=False, default=True)
    note: str | None = Field(default=None)
    category: str | None = Field(default=None)
    sub_category: str | None = Field(default=None)
    detail: str | None = Field(default=None)
    meal_type: str | None = Field(default=None)
    dedup_key: str = Field(nullable=False, unique=True)
    job_id: uuid.UUID = Field(nullable=True, default=None, foreign_key="jobs.id")


# TODO - check what happens when we try to insert batch with a few duplicates
def insert_transactions(transactions: list[Transaction], db: Engine) -> None:
    with Session(db) as session:
        session.add_all(transactions)
        session.commit()


# TODO - consider just using get all entries and caller would extract the keys from it.
def get_existing_dedup_keys(db: Engine) -> list[str]:
    with Session(db) as session:
        transactions = session.exec(select(Transaction))
        result = [transaction.dedup_key for transaction in transactions]
        return result

