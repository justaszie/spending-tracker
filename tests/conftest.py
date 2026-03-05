from decimal import Decimal
import datetime as dt
import uuid

from sqlmodel import SQLModel, StaticPool, create_engine
import pytest

from app.core.config import AppEnvironment, app_config
from app.core.project_types import (
    ExtractedTransaction,
    ImportableTransaction,
    Side,
    TransactionSource,
    TransactionType,
)
from app.db.transactions import Transaction


# Set APP_ENVIRONMENT to "TEST" to skip initializing external resources (e.g. Supabase)
# that are not needed
@pytest.fixture(autouse=True)
def force_test_environment(monkeypatch):
    monkeypatch.setenv("APP_ENVIRONMENT", AppEnvironment.TEST.value)
    app_config.APP_ENVIRONMENT = AppEnvironment.TEST


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


@pytest.fixture(scope="session")
def db_transaction():
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
            "manually_added": False,
            "note": "a cold pint",
            "dedup_key": "373601123123aasdasd123123",
            "user_id": uuid.uuid4(),
        }
        data.update(override_values)
        return Transaction(**data)

    return make


@pytest.fixture
def test_db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        # Using static pool to make sure all threads use the same connection
        # and the same in-memory DB
        poolclass=StaticPool,
    )

    # Import models so that metadata includes all tables, then create schema.
    SQLModel.metadata.create_all(engine)

    try:
        yield engine
    finally:
        SQLModel.metadata.drop_all(engine)
        engine.dispose()
