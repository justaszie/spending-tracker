from decimal import Decimal
import datetime as dt

import pytest

from app.core.project_types import (
    ExtractedTransaction,
    Side,
    TransactionSource,
    TransactionType,
)


@pytest.fixture(scope="session")
def extracted_transaction():
    def make(**override_values):
        data = {
            "transaction_datetime": dt.datetime.fromisoformat("2026-01-10T13:10:10"),
            "type": TransactionType.CARD_PAYMENT,
            "counterparty": "BrewDog Pub",
            "orig_amount": Decimal("6.55"),
            "orig_currency": "GBP",
            "side": Side.DEBIT,
            "source": TransactionSource.REVOLUT,
            "note": "a cold pint",
            "dedup_key": "373601123123aasdasd123123",
        }
        data.update(override_values)
        return ExtractedTransaction(**data)
    return make
