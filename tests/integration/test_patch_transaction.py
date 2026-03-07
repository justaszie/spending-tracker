import uuid

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.config import app_config
from app.core.dependencies import get_authenticated_user, get_db_engine
from app.main import app

TEST_USER_ID = uuid.UUID("e92460b8-c69a-4706-bf9c-addefd582836")


@pytest.fixture
def test_client(test_db):
    app.dependency_overrides[get_authenticated_user] = lambda: TEST_USER_ID
    app.dependency_overrides[get_db_engine] = lambda: test_db

    with TestClient(app) as client:
        try:
            yield client
        finally:
            app.dependency_overrides.clear()


def test_patch_transaction_updates_spending_category(
    test_client: TestClient, test_db, db_transaction
):
    """PATCH with spending_category then GET the same transaction to verify the update."""
    transaction = db_transaction(
        user_id=TEST_USER_ID,
        spending_category="GROCERIES",
    )
    with Session(test_db, expire_on_commit=False) as session:
        session.add(transaction)
        session.commit()
        session.refresh(transaction)

    transaction_id = transaction.id
    transactions_path = f"{app_config.V1_API_PREFIX}/transactions"
    patch_response = test_client.patch(
        f"{transactions_path}/{transaction_id}",
        json={"spending_category": "EATING_OUT"},
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["spending_category"] == "EATING_OUT"

    get_response = test_client.get(f"{transactions_path}/{transaction_id}")
    assert get_response.status_code == 200
    body = get_response.json()
    assert body["spending_category"] == "EATING_OUT"
