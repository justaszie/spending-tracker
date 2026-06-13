import datetime as dt
import uuid
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel
from sqlalchemy import Engine, Select, String, UniqueConstraint, cast, func, or_
from sqlalchemy.exc import IntegrityError
from sqlmodel import Date, Field, Session, SQLModel, col, select
from sqlmodel.sql.expression import SelectOfScalar

from app.core.project_types import (
    Side,
    TransactionSource,
    TransactionsSortField,
    TransactionType,
)


class TransactionInsertError(Exception):
    pass


class TransactionNotFoundError(Exception):
    pass


class DuplicateReimbursementError(Exception):
    pass


class Transaction(SQLModel, table=True):
    __tablename__ = "transactions"
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


class Reimbursement(SQLModel, table=True):
    __tablename__ = "reimbursements"

    debit_txn_id: uuid.UUID = Field(
        foreign_key="transactions.id",
        primary_key=True,
        nullable=False,
    )
    credit_txn_id: uuid.UUID = Field(
        foreign_key="transactions.id",
        primary_key=True,
        nullable=False,
    )
    user_id: uuid.UUID = Field(nullable=False)
    orig_reimbursed_amount: Decimal = Field(nullable=False)
    orig_reimbursed_ccy: str = Field(nullable=False)
    eur_reimbursed_amount: Decimal = Field(nullable=False)
    created_at: dt.datetime = Field(nullable=False, default_factory=dt.datetime.now)
    updated_at: dt.datetime = Field(nullable=False, default_factory=dt.datetime.now)


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
    user_id: uuid.UUID,
    db: Engine,
    offset: int = 0,
    limit: int | None = None,
    search: str | None = "",
    sort_by: TransactionsSortField | None = None,
    sort_order: Literal["asc", "desc"] | None = None,
    filters: dict[str, list[Any]] | None = None,
    no_category_only: bool | None = False,
) -> list[Transaction]:
    with Session(db) as session:
        statement = _build_transactions_query(
            user_id=user_id,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
            filters=filters,
            no_category_only=no_category_only,
        )
        statement = statement.offset(offset)

        if limit is not None:
            statement = statement.limit(limit)

        result = session.exec(statement).all()
        return list(result)


def get_total_count(
    user_id: uuid.UUID,
    db: Engine,
    search: str | None = "",
    filters: dict[str, list[Any]] | None = None,
    no_category_only: bool | None = False,
) -> int:
    with Session(db) as session:
        base_statement = _build_transactions_query(
            user_id=user_id,
            search=search,
            sort_by=None,
            sort_order=None,
            filters=filters,
            no_category_only=no_category_only,
        )
        subquery = base_statement.subquery()
        query = select(func.count()).select_from(subquery)
        return session.scalar(query) or 0


def get_transaction(
    transaction_id: uuid.UUID, user_id: uuid.UUID, db: Engine
) -> Transaction | None:
    """Return a single transaction for a user or None if not found."""
    with Session(db) as session:
        statement = select(Transaction).where(
            Transaction.id == transaction_id, Transaction.user_id == user_id
        )
        return session.exec(statement).first()


def get_distinct_spending_categories(
    db: Engine,
) -> set[str]:
    """Return distinct, non-null spending categories from existing data"""
    with Session(db) as session:
        statement = (
            select(Transaction.spending_category)
            .where(Transaction.spending_category.is_not(None))  # type: ignore
            .distinct()
        )
        result = session.exec(statement).all()
        return {category for category in result if category is not None}


def update_transaction(
    db: Engine,
    user_id: uuid.UUID,
    transaction_id: uuid.UUID,
    update_data: dict[str, Any],
) -> Transaction | None:
    """Returns updated Transaction or None if transaction not found"""
    with Session(db) as session:
        statement = select(Transaction).where(
            Transaction.user_id == user_id, Transaction.id == transaction_id
        )
        existing = session.exec(statement).one()

        if not existing:
            return None

        existing.sqlmodel_update(update_data)
        session.add(existing)
        session.commit()
        session.refresh(existing)

        return existing


def insert_reimbursement(
    *,
    db: Engine,
    user_id: uuid.UUID,
    debit_txn_id: uuid.UUID,
    credit_txn_id: uuid.UUID,
    orig_reimbursed_amount: Decimal,
    credit_orig_amount: Decimal,
    credit_orig_currency: str,
    credit_eur_amount: Decimal,
) -> Reimbursement:
    """Persist a Reimbursement linking one Debit to one Credit.

    `eur_reimbursed_amount` is pro-rated from the credit's already-stored
    EUR conversion to keep full reimbursements lossless and avoid an
    additional FX lookup. Raises DuplicateReimbursementError if the
    (debit_txn_id, credit_txn_id) composite PK already exists.
    """
    eur_reimbursed_amount = (
        credit_eur_amount * (orig_reimbursed_amount / credit_orig_amount)
    ).quantize(Decimal("0.01"))

    reimbursement = Reimbursement(
        debit_txn_id=debit_txn_id,
        credit_txn_id=credit_txn_id,
        user_id=user_id,
        orig_reimbursed_amount=orig_reimbursed_amount.quantize(Decimal("0.01")),
        orig_reimbursed_ccy=credit_orig_currency,
        eur_reimbursed_amount=eur_reimbursed_amount,
    )

    try:
        with Session(db, expire_on_commit=False) as session:
            session.add(reimbursement)
            session.commit()
            session.refresh(reimbursement)
    except IntegrityError as e:
        raise DuplicateReimbursementError(
            "Reimbursement already exists for this debit/credit pair"
        ) from e

    return reimbursement


def _build_transactions_query(
    user_id: uuid.UUID,
    search: str | None = "",
    sort_by: TransactionsSortField | None = None,
    sort_order: Literal["asc", "desc"] | None = None,
    filters: dict[str, list[Any]] | None = None,
    no_category_only: bool | None = False,
) -> SelectOfScalar[Transaction]:
    statement = select(Transaction).where(Transaction.user_id == user_id)

    if search and len(search) > 1:
        search_query = search.strip()
        # Case-insensitive match on id (as text), counterparty, spending_category, note
        search_filter = or_(
            cast(Transaction.id, String).ilike(f"%{search_query}%"),  # type: ignore[attr-defined]
            Transaction.counterparty.ilike(f"%{search_query}%"),  # type: ignore[attr-defined, union-attr]
            Transaction.spending_category.ilike(f"%{search_query}%"),  # type: ignore[attr-defined, union-attr]
            Transaction.note.ilike(f"%{search_query}%"),  # type: ignore[attr-defined, union-attr]
        )
        statement = statement.where(search_filter)

    if filters:
        for field_name, values in filters.items():
            # Skip empty value collections
            if not values:
                continue

            # Skip fields that are not in the Transaction model
            if not hasattr(Transaction, field_name):
                continue

            column = getattr(Transaction, field_name)
            normalized_values = [str(value).strip().lower() for value in values]
            statement = statement.where(
                func.lower(cast(column, String)).in_(normalized_values)
            )

    if no_category_only:
        statement = statement.where(Transaction.spending_category.is_(None))  # type: ignore[union-attr]

    sort_by = sort_by if sort_by else "transaction_datetime"
    sort_column = getattr(Transaction, sort_by)

    sort_order = sort_order if sort_order else "desc"
    if sort_order == "asc":
        statement = statement.order_by(sort_column.asc())  # type: ignore[attr-defined]
    else:
        statement = statement.order_by(sort_column.desc())  # type: ignore[attr-defined]

    return statement


class StatsData(BaseModel):
    eur_total_spend: Decimal
    eur_total_reimbursed: Decimal
    net_total_spend: Decimal
    earliest_txn_datetime: dt.datetime | None = None
    latest_txn_datetime: dt.datetime | None = None


class CategorySummary(BaseModel):
    spending_category: str | None  # There can be txns with no category
    eur_total_spend: Decimal
    eur_total_reimbursed: Decimal
    net_total_spend: Decimal


def get_total_spend_data(
    user_id: uuid.UUID,
    db: Engine,
    date_to: dt.date | None = None,
    date_from: dt.date | None = None,
) -> StatsData:
    """Returns total spent money, less any money that was reimbursed"""
    # Step 1: CTE to
    reimbursements = _build_reimbursements_query(user_id).subquery()
    # Step 2: query transactions, joining reimbursements CTE and get sum of money spent
    query = (
        select(  # type: ignore[call-overload]
            func.coalesce(func.sum(Transaction.eur_amount), 0).label("eur_total_spend"),
            func.coalesce(func.sum(reimbursements.c.eur_reimbursed_amount), 0).label(
                "eur_total_reimbursed"
            ),
            func.coalesce(
                func.sum(
                    Transaction.eur_amount
                    - func.coalesce(reimbursements.c.eur_reimbursed_amount, 0)
                ),
                0,
            ).label("net_total_spend"),
            func.min(Transaction.transaction_datetime).label("earliest_txn_datetime"),
            func.max(Transaction.transaction_datetime).label("latest_txn_datetime"),
        )
        .select_from(Transaction)
        .join(
            reimbursements,
            col(Transaction.id) == reimbursements.c.debit_txn_id,
            isouter=True,
        )
        .where(Transaction.user_id == user_id, Transaction.side == Side.DEBIT)
    )
    if date_from:
        query = query.where(Transaction.transaction_datetime >= date_from)
    # Converting the timestamp to date before comparison
    # because default SQL may convert date_to to midnight
    if date_to:
        query = query.where(cast(Transaction.transaction_datetime, Date) <= date_to)

    with Session(db) as session:
        stats_row = session.exec(query).one()
        (
            eur_total_spend,
            eur_total_reimbursed,
            net_total_spend,
            earliest_txn_datetime,
            latest_txn_datetime,
        ) = stats_row

    return StatsData(
        eur_total_spend=eur_total_spend,
        eur_total_reimbursed=eur_total_reimbursed,
        net_total_spend=net_total_spend,
        earliest_txn_datetime=earliest_txn_datetime,
        latest_txn_datetime=latest_txn_datetime,
    )


# [{"category": "GROCERIES", "eur_total_spend": 105, ""]
def get_spend_data_by_category(
    user_id: uuid.UUID,
    db: Engine,
    date_to: dt.date | None = None,
    date_from: dt.date | None = None,
) -> list[CategorySummary]:
    """Returns total spent money, less any money that was reimbursed broken down by categories"""
    # Step 1: CTE to
    reimbursements = _build_reimbursements_query(user_id).subquery()
    # Step 2: query transactions, joining reimbursements CTE and get sum of money spent
    query = (
        select(
            Transaction.spending_category,
            func.coalesce(func.sum(Transaction.eur_amount), 0).label("eur_total_spend"),
            func.coalesce(func.sum(reimbursements.c.eur_reimbursed_amount), 0).label(
                "eur_total_reimbursed"
            ),
            func.coalesce(
                func.sum(
                    Transaction.eur_amount
                    - func.coalesce(reimbursements.c.eur_reimbursed_amount, 0)
                ),
                0,
            ).label("net_total_spend"),
        )
        .select_from(Transaction)
        .join(
            reimbursements,
            col(Transaction.id) == reimbursements.c.debit_txn_id,
            isouter=True,
        )
        .where(Transaction.user_id == user_id, Transaction.side == Side.DEBIT)
    )
    if date_from:
        query = query.where(Transaction.transaction_datetime >= date_from)
    # Converting the timestamp to date before comparison
    # because default SQL may convert date_to to midnight
    if date_to:
        query = query.where(cast(Transaction.transaction_datetime, Date) <= date_to)

    query = query.group_by(col(Transaction.spending_category))

    with Session(db) as session:
        rows = session.exec(query).all()
        result = []
        for row in rows:
            (
                spending_category,
                eur_total_spend,
                eur_total_reimbursed,
                net_total_spend,
            ) = row
            result.append(
                CategorySummary(
                    spending_category=spending_category,
                    eur_total_spend=eur_total_spend,
                    eur_total_reimbursed=eur_total_reimbursed,
                    net_total_spend=net_total_spend,
                )
            )

        return result


def _build_reimbursements_query(user_id: uuid.UUID) -> Select:
    """Returns a query to get total reimbursed amount by transaction"""
    return (
        select(
            col(Reimbursement.debit_txn_id),
            func.sum(Reimbursement.eur_reimbursed_amount).label(
                "eur_reimbursed_amount"
            ),
        )
        .where(Reimbursement.user_id == user_id)
        .group_by(col(Reimbursement.debit_txn_id))
    )
