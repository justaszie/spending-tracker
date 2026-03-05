from decimal import Decimal
import datetime as dt
import uuid

from sqlalchemy import Engine, UniqueConstraint
from sqlmodel import Field, Session, SQLModel, select

from app.core.project_types import Side, TransactionSource, TransactionType


class TransactionInsertError(Exception):
    pass


class Transaction(SQLModel, table=True):
    __tablename__ = "transactions"  # type: ignore
    __table_args__ = (
        UniqueConstraint(
            "user_id", "dedup_key", name="uq_transaction_user_id_dedup_key"
        ),
    )

    id: uuid.UUID = Field(primary_key=True, default_factory=uuid.uuid4)
    transaction_datetime: dt.datetime = Field(nullable=False)
    type: TransactionType = Field(nullable=True, default=None)
    counterparty: str = Field(nullable=False)
    orig_amount: Decimal = Field(nullable=False)
    orig_currency: str = Field(nullable=False)
    side: Side = Field(nullable=False)
    source: TransactionSource = Field(nullable=False)
    eur_amount: Decimal = Field(nullable=False)
    manually_added: bool = Field(nullable=False, default=False)
    note: str | None = Field(default=None)
    spending_category: str | None = Field(default=None)
    meal_type: str | None = Field(default=None)
    dedup_key: str = Field(nullable=False)
    import_job_id: uuid.UUID = Field(
        nullable=True, default=None, foreign_key="statement_import_jobs.id"
    )
    user_id: uuid.UUID = Field(nullable=False, index=True)


def insert_transactions(transactions: list[Transaction], db: Engine) -> None:
    try:
        with Session(db, expire_on_commit=False) as session:
            # setting expire_on_commit=False allows to reuse
            # the Transaction instances in the client code (import job runner)
            session.add_all(transactions)
            session.commit()
    except Exception as e:
        raise TransactionInsertError(
            "Error while inserting transactions into database"
        ) from e


def get_existing_dedup_keys(user_id: uuid.UUID, db: Engine) -> set[str]:
    with Session(db) as session:
        statement = select(Transaction.dedup_key).where(Transaction.user_id == user_id)
        result = session.exec(statement).all()
        # Set allows O(1) lookups when separating new transactions from existing ones
        return set(result)

# The query can be used either with pagination params or without (limit = None)
# Pagination will be off if we need to use this for tests
def get_transactions(
    user_id: uuid.UUID, db: Engine, offset: int = 0, limit: int | None = None
) -> list[Transaction]:
    with Session(db) as session:
        statement = (
            select(Transaction)
            .where(Transaction.user_id == user_id)
            .order_by(Transaction.transaction_datetime.desc())
            .offset(offset)
        )
        if limit is not None:
            statement = statement.limit(limit)

        result = session.exec(statement).all()
        return list(result)
