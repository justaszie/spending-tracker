from decimal import Decimal
import datetime as dt
import uuid

from sqlmodel import SQLModel, create_engine
import pytest

from app.core.project_types import (
    ExtractedTransaction,
    ImportableTransaction,
    Side,
    TransactionSource,
    TransactionType,
)
from app.db.transactions import Transaction


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
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    # We need to import all data models to create a schema in the test db
    from app.db.statement_import_jobs import StatementImportJob
    from app.db.transactions import Transaction
    SQLModel.metadata.create_all(engine)
    try:
        yield engine
    finally:
        SQLModel.metadata.drop_all(engine)
