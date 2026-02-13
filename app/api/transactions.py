import logging
from fastapi import APIRouter
from app.core.dependencies import AuthDependency, DBDependency
from app.db.transactions import get_transactions, Transaction


router = APIRouter(prefix="/transactions", tags=["Transactions"])

logger = logging.getLogger(__name__)


@router.get("", response_model=list[Transaction])
def get_all_transactions(
    user_id: AuthDependency, db: DBDependency
) -> list[Transaction]:
    return get_transactions(user_id=user_id, db=db)

