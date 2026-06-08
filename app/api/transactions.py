import datetime as dt
import logging
from decimal import Decimal
from typing import Annotated, Literal, Self
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field, model_validator

from app.analytics import build_stats_query, generate_transactions_stats
from app.core.config import app_config
from app.core.dependencies import AuthDependency, DBDependency
from app.core.project_types import (
    PeriodPreset,
    PeriodStats,
    Side,
    StatsDeltas,
    TransactionsSortField,
)
from app.db.transactions import (
    DuplicateReimbursementError,
    Transaction,
    get_distinct_spending_categories,
    get_total_count,
    get_transaction,
    get_transactions,
    insert_reimbursement,
    update_transaction,
)

router = APIRouter(prefix="/transactions", tags=["Transactions"])
reimbursements_router = APIRouter(prefix="/reimbursements", tags=["Reimbursements"])

logger = logging.getLogger(__name__)


class TransactionsReadResponse(BaseModel):
    page: int
    size: int
    transactions: list[Transaction]
    total: int


class TransactionUpdate(BaseModel):
    # Design decision to set max_length limits to avoid
    # very long and granular spending-category and meal_type labels
    spending_category: str | None = Field(default=None, max_length=50)
    meal_type: str | None = Field(default=None, max_length=20)
    note: str | None = Field(default=None)


class TransactionsQueryParams(BaseModel):
    page: int = Field(default=1, gt=0)
    size: int = Field(
        default=app_config.DEFAULT_PAGE_SIZE, le=app_config.MAX_PAGE_SIZE, gt=0
    )
    search: str | None = None
    sort_by: TransactionsSortField | None = None
    sort_order: Literal["asc", "desc"] | None = None
    side: list[Side] | None = None
    spending_category: list[str] | None = None
    untagged_only: bool = False


class TransactionsStatsRequest(BaseModel):
    period: PeriodPreset
    # Dates only required if period is "custom"
    date_from: dt.date | None = None
    date_to: dt.date | None = None
    include_previous: bool = False

    @model_validator(mode="after")
    def dates_required_custom_period(self) -> Self:
        if (
            self.period == PeriodPreset.CUSTOM
            and self.date_from is None
            and self.date_to is None
        ):
            raise ValueError(
                'When period is "custom", at least one of the dates is required'
            )

        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise ValueError("date_from cannot be after date_to")

        return self


class TransactionsStatsResponse(BaseModel):
    period: PeriodPreset
    # if current_period is null, it means there is no data to work with
    current_period: PeriodStats | None = None
    # previous data & deltas are null when previous period doesn't exist or not requested
    previous_period: PeriodStats | None = None
    deltas: StatsDeltas | None = None


@router.get("", response_model=TransactionsReadResponse)
def get_all_transactions(
    query: Annotated[TransactionsQueryParams, Query()],
    user_id: AuthDependency,
    db: DBDependency,
) -> TransactionsReadResponse:
    offset = (query.page - 1) * query.size
    limit = query.size

    logger.info(f"Query Params: {query}")

    filters = {}
    if query.side:
        filters["side"] = [s.value for s in query.side]
    if query.spending_category:
        filters["spending_category"] = list(query.spending_category)

    transactions = get_transactions(
        user_id=user_id,
        db=db,
        offset=offset,
        limit=limit,
        search=query.search,
        sort_by=query.sort_by,
        sort_order=query.sort_order,
        filters=filters if filters else None,
        no_category_only=query.untagged_only,
    )
    total_count = get_total_count(
        user_id=user_id,
        db=db,
        search=query.search,
        filters=filters if filters else None,
        no_category_only=query.untagged_only,
    )
    return TransactionsReadResponse(
        transactions=transactions,
        page=query.page,
        size=query.size,
        total=total_count,
    )


@router.get("/{transaction_id:uuid}", response_model=Transaction)
def get_single_transaction(
    user_id: AuthDependency,
    transaction_id: UUID,
    db: DBDependency,
) -> Transaction:
    transaction = get_transaction(transaction_id=transaction_id, user_id=user_id, db=db)
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    return transaction


@router.get("/spending-categories", response_model=list[str])
def get_spending_categories(
    _: AuthDependency,
    db: DBDependency,
) -> list[str]:
    categories_set = get_distinct_spending_categories(db=db)
    return sorted(categories_set)


@router.patch("/{transaction_id:uuid}", response_model=Transaction)
def patch_transaction(
    user_id: AuthDependency,
    db: DBDependency,
    transaction_id: UUID,
    update_payload: TransactionUpdate,
) -> Transaction:
    update_data = update_payload.model_dump(exclude_unset=True)
    updated = update_transaction(
        db=db, user_id=user_id, transaction_id=transaction_id, update_data=update_data
    )

    if not updated:
        raise HTTPException(404, detail="Transaction not found")

    return updated


@router.get("/stats", response_model=TransactionsStatsResponse)
def get_transactions_stats(
    user_id: AuthDependency,
    db: DBDependency,
    params: Annotated[TransactionsStatsRequest, Query()],
) -> TransactionsStatsResponse:
    query = build_stats_query(
        user_id=user_id,
        date_from=params.date_from,
        date_to=params.date_to,
        selected_period=params.period,
        previous_requested=params.include_previous,
    )

    stats = generate_transactions_stats(query=query, db=db)

    return TransactionsStatsResponse(
        period=params.period,
        current_period=stats.current_period,
        previous_period=stats.previous_period,
        deltas=stats.deltas,
    )


class ReimbursementCreateRequest(BaseModel):
    debit_txn_id: UUID
    credit_txn_id: UUID
    orig_reimbursed_amount: Decimal = Field(gt=0)


class ReimbursementResponse(BaseModel):
    debit_txn_id: UUID
    credit_txn_id: UUID
    orig_reimbursed_amount: Decimal
    orig_reimbursed_ccy: str
    eur_reimbursed_amount: Decimal


@reimbursements_router.post("", response_model=ReimbursementResponse, status_code=201)
def create_reimbursement(
    user_id: AuthDependency,
    db: DBDependency,
    payload: ReimbursementCreateRequest,
) -> ReimbursementResponse:
    debit_txn = get_transaction(
        transaction_id=payload.debit_txn_id, user_id=user_id, db=db
    )
    if not debit_txn:
        raise HTTPException(status_code=404, detail="Debit transaction not found")

    credit_txn = get_transaction(
        transaction_id=payload.credit_txn_id, user_id=user_id, db=db
    )
    if not credit_txn:
        raise HTTPException(status_code=404, detail="Credit transaction not found")

    if debit_txn.side != Side.DEBIT:
        raise HTTPException(
            status_code=422,
            detail="debit_txn_id must reference a Debit transaction",
        )

    if credit_txn.side != Side.CREDIT:
        raise HTTPException(
            status_code=422,
            detail="credit_txn_id must reference a Credit transaction",
        )

    try:
        reimbursement = insert_reimbursement(
            db=db,
            user_id=user_id,
            debit_txn_id=debit_txn.id,
            credit_txn_id=credit_txn.id,
            orig_reimbursed_amount=payload.orig_reimbursed_amount,
            credit_orig_amount=credit_txn.orig_amount,
            credit_orig_currency=credit_txn.orig_currency,
            credit_eur_amount=credit_txn.eur_amount,
        )
    except DuplicateReimbursementError as e:
        raise HTTPException(
            status_code=409,
            detail="Reimbursement already exists for this debit/credit pair",
        ) from e

    return ReimbursementResponse(
        debit_txn_id=reimbursement.debit_txn_id,
        credit_txn_id=reimbursement.credit_txn_id,
        orig_reimbursed_amount=reimbursement.orig_reimbursed_amount.quantize(
            Decimal("0.01")
        ),
        orig_reimbursed_ccy=reimbursement.orig_reimbursed_ccy,
        eur_reimbursed_amount=reimbursement.eur_reimbursed_amount.quantize(
            Decimal("0.01")
        ),
    )
