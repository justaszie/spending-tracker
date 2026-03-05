from typing import Annotated
import logging

from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.core.config import app_config
from app.core.dependencies import AuthDependency, DBDependency
from app.db.transactions import Transaction, get_transactions

router = APIRouter(prefix="/transactions", tags=["Transactions"])

logger = logging.getLogger(__name__)


class TransactionsRead(BaseModel):
    page: int
    size: int
    transactions: list[Transaction]


@router.get("", response_model=TransactionsRead)
def get_all_transactions(
    user_id: AuthDependency,
    db: DBDependency,
    page: Annotated[int, Query(gt=0)] = 1,
    size: Annotated[
        int, Query(le=app_config.MAX_PAGE_SIZE, gt=0)
    ] = app_config.DEFAULT_PAGE_SIZE,
) -> TransactionsRead:
    offset = (page - 1) * size
    limit = size

    transactions = get_transactions(user_id=user_id, db=db, offset=offset, limit=limit)
    return TransactionsRead(
        transactions=transactions,
        page=page,
        size=size,
    )
