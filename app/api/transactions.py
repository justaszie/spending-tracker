import logging
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.core.config import app_config
from app.core.dependencies import AuthDependency, DBDependency
from app.core.project_types import Side, TransactionsSortField
from app.db.transactions import (
    Transaction,
    get_distinct_spending_categories,
    get_transaction,
    get_transactions,
    update_transaction,
)

router = APIRouter(prefix="/transactions", tags=["Transactions"])

logger = logging.getLogger(__name__)


class TransactionsRead(BaseModel):
    page: int
    size: int
    transactions: list[Transaction]


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


@router.get("", response_model=TransactionsRead)
def get_all_transactions(
    query: Annotated[TransactionsQueryParams, Query()],
    user_id: AuthDependency,
    db: DBDependency,
) -> TransactionsRead:
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
    return TransactionsRead(
        transactions=transactions,
        page=query.page,
        size=query.size,
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
