import re
from collections.abc import Callable

from app.core.project_types import ExtractedTransaction, TransactionType

OWN_ACCOUNT_NAMES = (
    r"^JUSTAS ZIEMINYKAS$",
    r"^TO GBP$",
    r"^TO GBP SAVINGS$",
    r"^TO JUSTAS Å½IEMINYKAS$",
    r"^TO JUSTAS ŽIEMINYKAS$",
    r"^TO JUSTAS ZIEMINYKAS$",
    r"^TO USD$",
    r"^TO INVESTMENT ACCOUNT$",
)

OWN_ACCOUNT_PATTERNS = tuple(
    re.compile(pattern, re.IGNORECASE) for pattern in OWN_ACCOUNT_NAMES
)

FilterRuleFN = Callable[[ExtractedTransaction], bool]


def is_own_account_transfer(transaction: ExtractedTransaction) -> bool:
    return any(
        pattern.search(transaction.counterparty) is not None
        for pattern in OWN_ACCOUNT_PATTERNS
    )


# Transaction passes filter (is kept) if the rule returns True
FILTER_RULES: list[FilterRuleFN] = [
    lambda txn: txn.type != TransactionType.CASH_WITHDRAWAL,
    lambda txn: not is_own_account_transfer(txn),
]


def get_filter_rules() -> list[FilterRuleFN]:
    return list(FILTER_RULES)
