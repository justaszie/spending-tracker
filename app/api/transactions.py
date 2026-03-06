import logging
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.core.config import app_config
from app.core.dependencies import AuthDependency, DBDependency
from app.core.project_types import TransactionsSortField
from app.db.transactions import (
    Transaction,
    get_distinct_spending_categories,
    get_transaction,
    get_transactions,
)

router = APIRouter(prefix="/transactions", tags=["Transactions"])

logger = logging.getLogger(__name__)


class TransactionsRead(BaseModel):
    page: int
    size: int
    transactions: list[Transaction]


class TransactionsQueryParams(BaseModel):
    page: Annotated[int, Query(default=1, gt=0)]
    size: Annotated[
        int,
        Query(default=app_config.DEFAULT_PAGE_SIZE, le=app_config.MAX_PAGE_SIZE, gt=0),
    ]
    search: str | None = ""
    sort_by: TransactionsSortField | None = None
    sort_order: Literal["asc", "desc"] | None = None


@router.get("", response_model=TransactionsRead)
def get_all_transactions(
    query: Annotated[TransactionsQueryParams, Query()],
    user_id: AuthDependency,
    db: DBDependency,
) -> TransactionsRead:
    offset = (query.page - 1) * query.size
    limit = query.size

    transactions = get_transactions(
        user_id=user_id,
        db=db,
        offset=offset,
        limit=limit,
        search=query.search,
        sort_by=query.sort_by,
        sort_order=query.sort_order,
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
