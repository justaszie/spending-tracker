import uuid
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.core.config import app_config
from app.core.dependencies import get_authenticated_user, get_db_engine
from app.core.project_types import Side
from app.db.transactions import Reimbursement
from app.main import app

TEST_USER_ID = uuid.UUID("e92460b8-c69a-4706-bf9c-addefd582836")
OTHER_USER_ID = uuid.UUID("11111111-2222-3333-4444-555555555555")

REIMBURSEMENTS_PATH = f"{app_config.V1_API_PREFIX}/reimbursements"
STATS_PATH = f"{app_config.V1_API_PREFIX}/transactions/stats"


@pytest.fixture
def test_client(test_db):
    app.dependency_overrides[get_authenticated_user] = lambda: TEST_USER_ID
    app.dependency_overrides[get_db_engine] = lambda: test_db

    with TestClient(app) as client:
        try:
            yield client
        finally:
            app.dependency_overrides.clear()


def _persist(test_db, *txns):
    with Session(test_db, expire_on_commit=False) as session:
        session.add_all(txns)
        session.commit()
        for txn in txns:
            session.refresh(txn)


def _make_debit(db_transaction, *, user_id=TEST_USER_ID, dedup_key="debit-1", **kwargs):
    defaults = dict(
        user_id=user_id,
        dedup_key=dedup_key,
        side=Side.DEBIT,
        orig_amount=Decimal("10.00"),
        orig_currency="EUR",
        eur_amount=Decimal("10.00"),
    )
    defaults.update(kwargs)
    return db_transaction(**defaults)


def _make_credit(
    db_transaction, *, user_id=TEST_USER_ID, dedup_key="credit-1", **kwargs
):
    defaults = dict(
        user_id=user_id,
        dedup_key=dedup_key,
        side=Side.CREDIT,
        orig_amount=Decimal("10.00"),
        orig_currency="EUR",
        eur_amount=Decimal("10.00"),
    )
    defaults.update(kwargs)
    return db_transaction(**defaults)


def test_happy_path_creates_reimbursement(test_client, test_db, db_transaction):
    debit = _make_debit(db_transaction)
    credit = _make_credit(db_transaction)
    _persist(test_db, debit, credit)

    response = test_client.post(
        REIMBURSEMENTS_PATH,
        json={
            "debit_txn_id": str(debit.id),
            "credit_txn_id": str(credit.id),
            "orig_reimbursed_amount": 10.0,
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body == {
        "debit_txn_id": str(debit.id),
        "credit_txn_id": str(credit.id),
        "orig_reimbursed_amount": "10.00",
        "orig_reimbursed_ccy": "EUR",
        "eur_reimbursed_amount": "10.00",
    }
    assert "user_id" not in body

    with Session(test_db) as session:
        rows = session.exec(select(Reimbursement)).all()
        assert len(rows) == 1
        row = rows[0]
        assert row.debit_txn_id == debit.id
        assert row.credit_txn_id == credit.id
        assert row.user_id == TEST_USER_ID
        assert row.orig_reimbursed_amount == Decimal("10.00")
        assert row.orig_reimbursed_ccy == "EUR"
        assert row.eur_reimbursed_amount == Decimal("10.00")


def test_pro_rate_math_on_non_eur_credit(test_client, test_db, db_transaction):
    debit = _make_debit(
        db_transaction,
        orig_amount=Decimal("50.00"),
        orig_currency="EUR",
        eur_amount=Decimal("50.00"),
    )
    credit = _make_credit(
        db_transaction,
        orig_amount=Decimal("40.00"),
        orig_currency="GBP",
        eur_amount=Decimal("50.00"),
    )
    _persist(test_db, debit, credit)

    response = test_client.post(
        REIMBURSEMENTS_PATH,
        json={
            "debit_txn_id": str(debit.id),
            "credit_txn_id": str(credit.id),
            "orig_reimbursed_amount": 20.0,
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["orig_reimbursed_amount"] == "20.00"
    assert body["orig_reimbursed_ccy"] == "GBP"
    assert body["eur_reimbursed_amount"] == "25.00"


def test_returns_404_when_debit_belongs_to_other_user(
    test_client, test_db, db_transaction
):
    debit = _make_debit(db_transaction, user_id=OTHER_USER_ID, dedup_key="debit-other")
    credit = _make_credit(db_transaction)
    _persist(test_db, debit, credit)

    response = test_client.post(
        REIMBURSEMENTS_PATH,
        json={
            "debit_txn_id": str(debit.id),
            "credit_txn_id": str(credit.id),
            "orig_reimbursed_amount": 5.0,
        },
    )

    assert response.status_code == 404


def test_returns_404_when_credit_belongs_to_other_user(
    test_client, test_db, db_transaction
):
    debit = _make_debit(db_transaction)
    credit = _make_credit(
        db_transaction, user_id=OTHER_USER_ID, dedup_key="credit-other"
    )
    _persist(test_db, debit, credit)

    response = test_client.post(
        REIMBURSEMENTS_PATH,
        json={
            "debit_txn_id": str(debit.id),
            "credit_txn_id": str(credit.id),
            "orig_reimbursed_amount": 5.0,
        },
    )

    assert response.status_code == 404


def test_returns_422_when_debit_id_points_at_credit_row(
    test_client, test_db, db_transaction
):
    # debit_txn_id actually references a Credit-side transaction
    not_a_debit = _make_credit(db_transaction, dedup_key="actually-credit")
    credit = _make_credit(db_transaction, dedup_key="real-credit")
    _persist(test_db, not_a_debit, credit)

    response = test_client.post(
        REIMBURSEMENTS_PATH,
        json={
            "debit_txn_id": str(not_a_debit.id),
            "credit_txn_id": str(credit.id),
            "orig_reimbursed_amount": 5.0,
        },
    )

    assert response.status_code == 422


def test_returns_422_when_amount_not_positive(test_client, test_db, db_transaction):
    debit = _make_debit(db_transaction)
    credit = _make_credit(db_transaction)
    _persist(test_db, debit, credit)

    response = test_client.post(
        REIMBURSEMENTS_PATH,
        json={
            "debit_txn_id": str(debit.id),
            "credit_txn_id": str(credit.id),
            "orig_reimbursed_amount": 0,
        },
    )

    assert response.status_code == 422


def test_returns_409_on_duplicate_pair(test_client, test_db, db_transaction):
    debit = _make_debit(db_transaction)
    credit = _make_credit(db_transaction)
    _persist(test_db, debit, credit)

    payload = {
        "debit_txn_id": str(debit.id),
        "credit_txn_id": str(credit.id),
        "orig_reimbursed_amount": 5.0,
    }

    first = test_client.post(REIMBURSEMENTS_PATH, json=payload)
    assert first.status_code == 201

    second = test_client.post(REIMBURSEMENTS_PATH, json=payload)
    assert second.status_code == 409


def test_stats_round_trip_reflects_reimbursement(test_client, test_db, db_transaction):
    debit = _make_debit(
        db_transaction,
        orig_amount=Decimal("100.00"),
        orig_currency="EUR",
        eur_amount=Decimal("100.00"),
    )
    credit = _make_credit(
        db_transaction,
        orig_amount=Decimal("40.00"),
        orig_currency="EUR",
        eur_amount=Decimal("40.00"),
    )
    _persist(test_db, debit, credit)

    before = test_client.get(STATS_PATH, params={"period": "ALL_TIME"})
    assert before.status_code == 200
    before_total = Decimal(before.json()["current_period"]["groups"]["spend"]["total"])
    assert before_total == Decimal("100.00")

    post_response = test_client.post(
        REIMBURSEMENTS_PATH,
        json={
            "debit_txn_id": str(debit.id),
            "credit_txn_id": str(credit.id),
            "orig_reimbursed_amount": 25.0,
        },
    )
    assert post_response.status_code == 201

    after = test_client.get(STATS_PATH, params={"period": "ALL_TIME"})
    assert after.status_code == 200
    after_total = Decimal(after.json()["current_period"]["groups"]["spend"]["total"])
    assert after_total == Decimal("75.00")
    assert before_total - after_total == Decimal("25.00")
