import uuid
from decimal import Decimal

import pytest
from sqlmodel import Session, select

from app.db.transactions import (
    Transaction,
    TransactionInsertError,
    get_existing_dedup_keys,
    insert_transactions,
)


@pytest.fixture(scope="module")
def sample_transactions(db_transaction):
    return [
        db_transaction(
            counterparty="Subway",
            dedup_key="dbfcfd0d87220f629339bd3adcf452d083fde3246625fb3a93e314f833e20d37",
        ),
        db_transaction(
            counterparty="KFC",
            dedup_key="4bdd0bbfe3f4c52cc2c8ff02f1fef29663dd9938f230304915805af1fa71e968",
        ),
    ]


class TestInsertTransactions:
    def test_inserts_transactions(self, test_db, sample_transactions):
        insert_transactions(transactions=sample_transactions, db=test_db)

        # Verify that all transactions inserted
        with Session(test_db) as session:
            result = session.exec(select(Transaction)).all()

        assert len(result) == 2
        assert isinstance(result[0].id, uuid.UUID)

    def test_insert_empty_list_does_not_change_db(self, test_db):
        with Session(test_db) as session:
            initial_count = len(session.exec(select(Transaction)).all())

        insert_transactions(transactions=[], db=test_db)

        with Session(test_db) as session:
            final_count = len(session.exec(select(Transaction)).all())

        assert final_count == initial_count

    def test_raises_standard_exception(
        self,
        db_transaction,
    ):
        with pytest.raises(TransactionInsertError):
            # Sending a wrong value for db engine param will raise an exception
            insert_transactions(transactions=[db_transaction()], db="wrong")

    def test_inserts_amounts_with_two_decimals(self, test_db, db_transaction):
        # We assume that the users of Transaction DB model will provide
        # properly quantized amounts i.e. (2 decimals).
        # The quantization is done when the data is validated at the boundary
        # (e.g. when parsing a statement file)
        txn = db_transaction(
            orig_amount=Decimal("8.56"),
            eur_amount=Decimal("8.99"),
        )

        insert_transactions(transactions=[txn], db=test_db)

        with Session(test_db) as session:
            result = session.exec(select(Transaction)).all()

        assert len(result) == 1
        stored = result[0]
        assert stored.orig_amount == Decimal("8.56")
        assert stored.eur_amount == Decimal("8.99")

    # It's possible for multiple users to have transactions with same data (i.e. same dedup key)
    def test_allows_inserting_same_dedup_key_different_users(
        self, test_db, db_transaction
    ):
        dedup_key = "same-dedup-key"
        first_user_id = uuid.uuid4()
        second_user_id = uuid.uuid4()

        transactions = [
            db_transaction(user_id=first_user_id, dedup_key=dedup_key),
            db_transaction(user_id=second_user_id, dedup_key=dedup_key),
        ]

        insert_transactions(transactions=transactions, db=test_db)

        with Session(test_db) as session:
            result = session.exec(select(Transaction)).all()

        assert len(result) == 2
        assert {t.user_id for t in result} == {first_user_id, second_user_id}

    def test_rejects_inserting_same_dedup_key_same_user(self, test_db, db_transaction):
        with Session(test_db) as session:
            initial_count = len(session.exec(select(Transaction)).all())

        user_id = uuid.uuid4()
        dedup_key = "duplicate-dedup-key"

        transactions = [
            db_transaction(user_id=user_id, dedup_key=dedup_key),
            db_transaction(user_id=user_id, dedup_key=dedup_key),
        ]

        with pytest.raises(TransactionInsertError):
            insert_transactions(transactions=transactions, db=test_db)

        with Session(test_db) as session:
            result = session.exec(select(Transaction)).all()

        assert len(result) == initial_count


class TestGetDedupKeys:
    def test_returns_existing_dedup_keys_per_user(self, test_db, db_transaction):
        target_user_id = uuid.uuid4()
        other_user_id = uuid.uuid4()

        transactions = [
            db_transaction(user_id=target_user_id, dedup_key="key-1"),
            db_transaction(user_id=target_user_id, dedup_key="key-2"),
            db_transaction(user_id=other_user_id, dedup_key="key-1"),
            db_transaction(user_id=other_user_id, dedup_key="key-3"),
        ]

        insert_transactions(transactions=transactions, db=test_db)

        existing_keys = get_existing_dedup_keys(user_id=target_user_id, db=test_db)

        assert existing_keys == {"key-1", "key-2"}
        assert isinstance(existing_keys, set)

    def test_returns_empty_set_when_no_data(self, test_db):
        random_user_id = uuid.uuid4()

        existing_keys = get_existing_dedup_keys(user_id=random_user_id, db=test_db)

        assert existing_keys == set()
