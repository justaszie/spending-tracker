from decimal import Decimal
import datetime as dt

import pytest

from app.core.project_types import (
    ExtractedTransaction,
    ImportableTransaction,
    Side,
    TransactionSource,
    TransactionType,
)


@pytest.fixture(scope="session")
def importable_transaction():
    def make(**override_values):
        data = {
            "transaction_datetime": dt.datetime.fromisoformat("2026-01-10T13:10:10"),
            "type": TransactionType.CARD_PAYMENT,
            "counterparty": "BrewDog Pub",
            "orig_amount": Decimal("6.55"),
            "orig_currency": "GBP",
            "eur_amount": Decimal("7.55"),
            "side": Side.DEBIT,
            "source": TransactionSource.REVOLUT,
            "note": "a cold pint",
            "dedup_key": "373601123123aasdasd123123",
        }
        data.update(override_values)
        return ImportableTransaction(**data)
    return make
