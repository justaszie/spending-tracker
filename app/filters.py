# Responsibility: implement filters (WHAT) and filtering logic (HOW)
# for a set of extracted transactions.
from collections.abc import Callable
import copy
import re

from app.project_types import ExtractedTransaction, TransactionType

OWN_ACCOUNT_NAMES = (
    r"^JUSTAS ZIEMINYKAS$",
    r"^TO GBP$",
    r"^TO GBP SAVINGS$",
    r"^TO JUSTAS Å½IEMINYKAS$",
    r"^TO JUSTAS ŽIEMINYKAS$",
    r"^TO JUSTAS ZIEMINYKAS$",
    r"^TO USD$",
    r"^TO INVESTMENT ACCOUNT$",
    r"^Revolut\*\*6494\* E14 4HD London$",  # Top up using Google Play with Swedbank card
)

OWN_ACCOUNT_PATTERNS = tuple(
    re.compile(pattern, re.IGNORECASE) for pattern in OWN_ACCOUNT_NAMES
)

FilterFN = Callable[[ExtractedTransaction], bool]


def is_own_account_transfer(transaction: ExtractedTransaction) -> bool:
    return transaction.type == TransactionType.TRANSFER and any(
        pattern.search(transaction.counterparty) is not None
        for pattern in OWN_ACCOUNT_PATTERNS
    )


ACTIVE_FILTERS: list[FilterFN] = [
    # lambda txn: txn.type != TransactionType.CASH_WITHDRAWAL,
    lambda txn: not is_own_account_transfer(txn),
]


def get_all_filters() -> list[FilterFN]:
    return list(copy.deepcopy(ACTIVE_FILTERS))


def filter_transactions(
    transactions: list[ExtractedTransaction],
) -> list[ExtractedTransaction]:
    filters = get_all_filters()
    filtered = [
        txn
        for txn in transactions
        if all(filter_function(txn) for filter_function in filters)
    ]

    return filtered
