import random
import uuid
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.config import app_config
from app.core.dependencies import get_authenticated_user, get_db_engine
from app.main import app

TEST_USER_ID = uuid.UUID("e92460b8-c69a-4706-bf9c-addefd582836")


IMPORT_API_PATH = f"{app_config.V1_API_PREFIX}/statement-imports"


@pytest.fixture
def test_client(test_db):
    app.dependency_overrides[get_authenticated_user] = lambda: TEST_USER_ID
    app.dependency_overrides[get_db_engine] = lambda: test_db

    with TestClient(app) as client:
        try:
            yield client
        finally:
            app.dependency_overrides.clear()


def random_datetime(year: int = 2025) -> datetime:
    """
    Return a random datetime within the given calendar year.
    The range is [year-01-01 00:00:00, (year+1)-01-01 00:00:00).
    """
    start = datetime(year, 1, 1)
    # Use the first moment of the following year as an exclusive upper bound.
    # This avoids off-by-one issues with days in the year (including leap years).
    start_next_year = datetime(year + 1, 1, 1)

    total_seconds = int((start_next_year - start).total_seconds())
    random_offset = random.randrange(total_seconds)

    return start + timedelta(seconds=random_offset)


def random_dedup_key() -> str:
    """Return a random deduplication key to help create a batch of unique transaction records"""
    return str(uuid.uuid4())


class TestGetTransactions:
    TRANSACTIONS_API_PATH = f"{app_config.V1_API_PREFIX}/transactions"

    def _insert_random_transactions(self, test_db, db_transaction, count: int) -> list:
        inserted_txns = [
            db_transaction(
                transaction_datetime=random_datetime(2025),
                user_id=TEST_USER_ID,
                dedup_key=random_dedup_key(),
            )
            for _ in range(count)
        ]

        with Session(test_db, expire_on_commit=False) as session:
            session.add_all(inserted_txns)
            session.commit()

        return sorted(
            inserted_txns,
            key=lambda txn: txn.transaction_datetime,
            reverse=True,
        )

    def _page_data_as_expected(
        self,
        body: dict,
        sorted_txns: list,
        page: int,
        size: int,
    ) -> None:
        # Verifying that 1st and last transactions in the response match the expected transactions
        first_idx = (page - 1) * size
        last_idx = (page * size) - 1
        first_of_page = sorted_txns[first_idx]
        last_of_page = sorted_txns[last_idx]

        assert body["transactions"][0]["dedup_key"] == first_of_page.dedup_key
        assert body["transactions"][-1]["dedup_key"] == last_of_page.dedup_key

    @pytest.mark.parametrize(
        ("page", "size"),
        [
            (1, 10),
            (3, 15),
        ],
    )
    def test_returns_paginated_data(
        self, test_client, test_db, db_transaction, page, size
    ):
        # Test only makes sense if we insert enough data for the page params
        insert_count = page * size + 10
        sorted_txns = self._insert_random_transactions(
            test_db=test_db,
            db_transaction=db_transaction,
            count=insert_count,
        )

        response = test_client.get(
            self.TRANSACTIONS_API_PATH,
            params={"page": page, "size": size},
        )
        assert response.status_code == 200
        body = response.json()

        assert body["page"] == page
        assert body["size"] == size
        assert len(body["transactions"]) == size

        self._page_data_as_expected(
            body=body,
            sorted_txns=sorted_txns,
            page=page,
            size=size,
        )

    def test_uses_first_page_when_page_not_provided(
        self,
        test_client,
        test_db,
        db_transaction,
    ):
        size = 10
        insert_count = 3 * size
        sorted_txns = self._insert_random_transactions(
            test_db=test_db,
            db_transaction=db_transaction,
            count=insert_count,
        )

        response = test_client.get(self.TRANSACTIONS_API_PATH, params={"size": size})
        assert response.status_code == 200

        body = response.json()
        # page should default to 1
        assert body["page"] == 1
        assert body["size"] == size
        assert len(body["transactions"]) == size

        self._page_data_as_expected(
            body=body,
            sorted_txns=sorted_txns,
            page=1,
            size=size,
        )

    def test_uses_default_size_when_size_not_provided(
        self,
        test_client,
        test_db,
        db_transaction,
    ):
        page = 1
        default_size = app_config.DEFAULT_PAGE_SIZE
        insert_count = default_size + 10
        sorted_txns = self._insert_random_transactions(
            test_db=test_db,
            db_transaction=db_transaction,
            count=insert_count,
        )

        response = test_client.get(self.TRANSACTIONS_API_PATH, params={"page": page})
        assert response.status_code == 200

        body = response.json()
        assert body["page"] == page
        assert body["size"] == default_size
        assert len(body["transactions"]) == default_size

        self._page_data_as_expected(
            body=body,
            sorted_txns=sorted_txns,
            page=page,
            size=default_size,
        )

    @pytest.mark.parametrize("page", [0, -2])
    def test_invalid_page_returns_422(self, test_client, page):
        response = test_client.get(
            self.TRANSACTIONS_API_PATH, params={"page": page, "size": 10}
        )
        assert response.status_code == 422

    @pytest.mark.parametrize("size", [0, -5, app_config.MAX_PAGE_SIZE + 1])
    def test_invalid_size_returns_422(self, test_client, size):
        response = test_client.get(
            self.TRANSACTIONS_API_PATH, params={"page": 1, "size": size}
        )
        assert response.status_code == 422

    def test_requesting_more_transactions_than_exist_returns_empty_list(
        self,
        test_client,
        test_db,
        db_transaction,
    ):
        # Insert fewer transactions than the requested page would cover
        existing_count = 10
        page = 5
        size = 10
        inserted_txns = [
            db_transaction(
                transaction_datetime=random_datetime(2025),
                user_id=TEST_USER_ID,
                dedup_key=random_dedup_key(),
            )
            for _ in range(existing_count)
        ]

        with Session(test_db, expire_on_commit=False) as session:
            session.add_all(inserted_txns)
            session.commit()

        response = test_client.get(
            self.TRANSACTIONS_API_PATH, params={"page": page, "size": size}
        )
        assert response.status_code == 200

        body = response.json()
        assert body["page"] == page
        assert body["size"] == size
        assert body["transactions"] == []

    def test_total_matches_number_of_transactions_without_filters(
        self,
        test_client,
        test_db,
        db_transaction,
    ):
        total_txns = 25
        page = 1
        size = 10

        self._insert_random_transactions(
            test_db=test_db,
            db_transaction=db_transaction,
            count=total_txns,
        )

        response = test_client.get(
            self.TRANSACTIONS_API_PATH,
            params={"page": page, "size": size},
        )
        assert response.status_code == 200

        body = response.json()
        assert body["page"] == page
        assert body["size"] == size
        assert len(body["transactions"]) == size
        assert body["total"] == total_txns

    @pytest.mark.parametrize(
        "field", ["id", "counterparty", "spending_category", "note"]
    )
    def test_search_finds_matching_transactions(
        self,
        test_client,
        test_db,
        db_transaction,
        field,
    ):
        matching = db_transaction(
            user_id=TEST_USER_ID,
            dedup_key=f"match-{field}",
            counterparty="ACME CORP",
            spending_category="GROCERIES",
            note="Lunch at Subway",
        )
        non_matching = db_transaction(
            user_id=TEST_USER_ID,
            dedup_key=f"other-{field}",
            counterparty="Different Merchant",
            spending_category="TRANSPORT",
            note="No match here",
        )

        with Session(test_db, expire_on_commit=False) as session:
            session.add_all([matching, non_matching])
            session.commit()
            session.refresh(matching)

        if field == "id":
            search_value = str(matching.id).split("-")[0]
        elif field == "counterparty":
            search_value = "acme"
        elif field == "spending_category":
            search_value = "groc"
        elif field == "note":
            search_value = "subway"

        response = test_client.get(
            self.TRANSACTIONS_API_PATH,
            params={"page": 1, "size": 50, "search": search_value},
        )
        assert response.status_code == 200
        body = response.json()
        assert [t["dedup_key"] for t in body["transactions"]] == [matching.dedup_key]

        # Total should reflect all matching rows, not just the page size.
        assert body["total"] == 1

    def test_search_returns_empty_list_when_no_match(
        self,
        test_client,
        test_db,
        db_transaction,
    ):
        txns = [
            db_transaction(
                user_id=TEST_USER_ID,
                dedup_key="txn-1",
                counterparty="Merchant One",
                spending_category="BILLS",
                note="something",
            ),
            db_transaction(
                user_id=TEST_USER_ID,
                dedup_key="txn-2",
                counterparty="Merchant Two",
                spending_category="TRANSPORT",
                note="another",
            ),
        ]
        with Session(test_db, expire_on_commit=False) as session:
            session.add_all(txns)
            session.commit()

        response = test_client.get(
            self.TRANSACTIONS_API_PATH,
            params={"page": 1, "size": 50, "search": "definitely-not-present"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["transactions"] == []

    @pytest.mark.parametrize(
        ("sort_by", "sort_order", "expected_dedup_keys"),
        [
            ("transaction_datetime", "asc", ["a", "b", "c"]),
            ("transaction_datetime", "desc", ["c", "b", "a"]),
            ("counterparty", "asc", ["a", "b", "c"]),
            ("counterparty", "desc", ["c", "b", "a"]),
            ("spending_category", "asc", ["a", "b", "c"]),
            ("spending_category", "desc", ["c", "b", "a"]),
            # Side values are stored/sorted as strings ("credit" < "debit").
            ("side", "asc", ["a", "c", "b"]),
            ("side", "desc", ["b", "a", "c"]),
            ("eur_amount", "asc", ["a", "b", "c"]),
            ("eur_amount", "desc", ["c", "b", "a"]),
        ],
    )
    def test_sorting_happy_paths(
        self,
        test_client,
        test_db,
        db_transaction,
        sort_by,
        sort_order,
        expected_dedup_keys,
    ):
        txn_a = db_transaction(
            user_id=TEST_USER_ID,
            dedup_key="a",
            transaction_datetime=datetime.fromisoformat("2026-01-01T10:00:00"),
            counterparty="A Merchant",
            spending_category="A_CATEGORY",
            side="credit",
            eur_amount="1.00",
        )
        txn_b = db_transaction(
            user_id=TEST_USER_ID,
            dedup_key="b",
            transaction_datetime=datetime.fromisoformat("2026-01-02T10:00:00"),
            counterparty="B Merchant",
            spending_category="B_CATEGORY",
            side="debit",
            eur_amount="2.00",
        )
        txn_c = db_transaction(
            user_id=TEST_USER_ID,
            dedup_key="c",
            transaction_datetime=datetime.fromisoformat("2026-01-03T10:00:00"),
            counterparty="C Merchant",
            spending_category="C_CATEGORY",
            side="credit",
            eur_amount="3.00",
        )

        with Session(test_db, expire_on_commit=False) as session:
            session.add_all([txn_a, txn_b, txn_c])
            session.commit()

        response = test_client.get(
            self.TRANSACTIONS_API_PATH,
            params={
                "page": 1,
                "size": 50,
                "sort_by": sort_by,
                "sort_order": sort_order,
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert [t["dedup_key"] for t in body["transactions"]] == expected_dedup_keys

    def test_invalid_sort_by_returns_422(self, test_client):
        response = test_client.get(
            self.TRANSACTIONS_API_PATH,
            params={"page": 1, "size": 10, "sort_by": "not_a_real_field"},
        )
        assert response.status_code == 422

    def test_invalid_sort_order_returns_422(self, test_client):
        response = test_client.get(
            self.TRANSACTIONS_API_PATH,
            params={"page": 1, "size": 10, "sort_order": "up"},
        )
        assert response.status_code == 422

    def test_side_filter_returns_only_debit_transactions(
        self,
        test_client,
        test_db,
        db_transaction,
    ):
        debit_txn = db_transaction(
            user_id=TEST_USER_ID,
            dedup_key="debit-only",
            side="debit",
        )
        credit_txn = db_transaction(
            user_id=TEST_USER_ID,
            dedup_key="credit-only",
            side="credit",
        )
        with Session(test_db, expire_on_commit=False) as session:
            session.add_all([debit_txn, credit_txn])
            session.commit()

        response = test_client.get(
            self.TRANSACTIONS_API_PATH,
            params={"page": 1, "size": 50, "side": ["debit"]},
        )
        assert response.status_code == 200
        body = response.json()
        assert len(body["transactions"]) == 1
        assert body["transactions"][0]["dedup_key"] == debit_txn.dedup_key
        assert body["transactions"][0]["side"] == "debit"
        assert body["total"] == 1

    def test_side_filter_returns_only_credit_transactions(
        self,
        test_client,
        test_db,
        db_transaction,
    ):
        debit_txn = db_transaction(
            user_id=TEST_USER_ID,
            dedup_key="debit-only",
            side="debit",
        )
        credit_txn = db_transaction(
            user_id=TEST_USER_ID,
            dedup_key="credit-only",
            side="credit",
        )
        with Session(test_db, expire_on_commit=False) as session:
            session.add_all([debit_txn, credit_txn])
            session.commit()

        response = test_client.get(
            self.TRANSACTIONS_API_PATH,
            params={"page": 1, "size": 50, "side": ["credit"]},
        )
        assert response.status_code == 200
        body = response.json()
        assert len(body["transactions"]) == 1
        assert body["transactions"][0]["dedup_key"] == credit_txn.dedup_key
        assert body["transactions"][0]["side"] == "credit"

    def test_side_filter_multiple_values_returns_both(
        self,
        test_client,
        test_db,
        db_transaction,
    ):
        debit_txn = db_transaction(
            user_id=TEST_USER_ID,
            dedup_key="debit-only",
            side="debit",
        )
        credit_txn = db_transaction(
            user_id=TEST_USER_ID,
            dedup_key="credit-only",
            side="credit",
        )
        with Session(test_db, expire_on_commit=False) as session:
            session.add_all([debit_txn, credit_txn])
            session.commit()

        response = test_client.get(
            self.TRANSACTIONS_API_PATH,
            params={"page": 1, "size": 50, "side": ["debit", "credit"]},
        )
        assert response.status_code == 200
        body = response.json()
        assert len(body["transactions"]) == 2
        dedup_keys = {t["dedup_key"] for t in body["transactions"]}
        assert dedup_keys == {debit_txn.dedup_key, credit_txn.dedup_key}

    def test_spending_category_filter_returns_only_matching(
        self,
        test_client,
        test_db,
        db_transaction,
    ):
        groceries_txn = db_transaction(
            user_id=TEST_USER_ID,
            dedup_key="groceries",
            spending_category="GROCERIES",
        )
        transport_txn = db_transaction(
            user_id=TEST_USER_ID,
            dedup_key="transport",
            spending_category="TRANSPORT",
        )
        with Session(test_db, expire_on_commit=False) as session:
            session.add_all([groceries_txn, transport_txn])
            session.commit()

        response = test_client.get(
            self.TRANSACTIONS_API_PATH,
            params={"page": 1, "size": 50, "spending_category": ["GROCERIES"]},
        )
        assert response.status_code == 200
        body = response.json()
        assert len(body["transactions"]) == 1
        assert body["transactions"][0]["dedup_key"] == groceries_txn.dedup_key
        assert body["transactions"][0]["spending_category"] == "GROCERIES"
        assert body["total"] == 1

    def test_untagged_only_returns_only_null_spending_category(
        self,
        test_client,
        test_db,
        db_transaction,
    ):
        tagged_txn = db_transaction(
            user_id=TEST_USER_ID,
            dedup_key="tagged",
            spending_category="GROCERIES",
        )
        untagged_txn = db_transaction(
            user_id=TEST_USER_ID,
            dedup_key="untagged",
            spending_category=None,
        )
        with Session(test_db, expire_on_commit=False) as session:
            session.add_all([tagged_txn, untagged_txn])
            session.commit()

        response = test_client.get(
            self.TRANSACTIONS_API_PATH,
            params={"page": 1, "size": 50, "untagged_only": True},
        )
        assert response.status_code == 200
        body = response.json()
        assert len(body["transactions"]) == 1
        assert body["transactions"][0]["dedup_key"] == untagged_txn.dedup_key
        assert body["transactions"][0]["spending_category"] is None

    def test_untagged_only_with_side_filter(
        self,
        test_client,
        test_db,
        db_transaction,
    ):
        """untagged_only=true and side=debit returns only debit transactions with null spending_category."""
        debit_tagged = db_transaction(
            user_id=TEST_USER_ID,
            dedup_key="debit-tagged",
            side="debit",
            spending_category="BILLS",
        )
        debit_untagged = db_transaction(
            user_id=TEST_USER_ID,
            dedup_key="debit-untagged",
            side="debit",
            spending_category=None,
        )
        credit_untagged = db_transaction(
            user_id=TEST_USER_ID,
            dedup_key="credit-untagged",
            side="credit",
            spending_category=None,
        )
        with Session(test_db, expire_on_commit=False) as session:
            session.add_all([debit_tagged, debit_untagged, credit_untagged])
            session.commit()

        response = test_client.get(
            self.TRANSACTIONS_API_PATH,
            params={"page": 1, "size": 50, "side": ["debit"], "untagged_only": True},
        )
        assert response.status_code == 200
        body = response.json()
        assert len(body["transactions"]) == 1
        assert body["transactions"][0]["dedup_key"] == debit_untagged.dedup_key
        assert body["transactions"][0]["side"] == "debit"
        assert body["transactions"][0]["spending_category"] is None

    def test_untagged_only_returns_empty_when_all_tagged(
        self,
        test_client,
        test_db,
        db_transaction,
    ):
        txn = db_transaction(
            user_id=TEST_USER_ID,
            dedup_key="only-tagged",
            spending_category="GROCERIES",
        )
        with Session(test_db, expire_on_commit=False) as session:
            session.add(txn)
            session.commit()

        response = test_client.get(
            self.TRANSACTIONS_API_PATH,
            params={"page": 1, "size": 50, "untagged_only": True},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["transactions"] == []


class TestGetSingleTransaction:
    TRANSACTIONS_API_PATH = f"{app_config.V1_API_PREFIX}/transactions"

    def test_returns_single_transaction_for_current_user(
        self,
        test_client,
        test_db,
        db_transaction,
    ):
        # Arrange: insert a single transaction for the authenticated user
        txn = db_transaction(
            user_id=TEST_USER_ID,
            dedup_key=random_dedup_key(),
        )

        with Session(test_db, expire_on_commit=False) as session:
            session.add(txn)
            session.commit()
            session.refresh(txn)

        # Act
        response = test_client.get(f"{self.TRANSACTIONS_API_PATH}/{txn.id}")

        # Assert
        assert response.status_code == 200
        body = response.json()
        assert uuid.UUID(body["id"]) == txn.id
        assert uuid.UUID(body["user_id"]) == txn.user_id

    def test_returns_404_when_transaction_not_found(
        self,
        test_client,
    ):
        non_existent_id = uuid.uuid4()

        response = test_client.get(f"{self.TRANSACTIONS_API_PATH}/{non_existent_id}")

        assert response.status_code == 404


class TestGetSpendingCategories:
    TRANSACTIONS_API_PATH = f"{app_config.V1_API_PREFIX}/transactions"

    def test_returns_distinct_spending_categories(
        self,
        test_client,
        test_db,
        db_transaction,
    ):
        inserted_txns = [
            db_transaction(
                spending_category="GROCERIES",
            ),
            db_transaction(
                spending_category="FOOD_DELIVERY",
            ),
            # Duplicate category should not appear twice
            db_transaction(
                spending_category="GROCERIES",
            ),
            # None should be ignored
            db_transaction(
                spending_category=None,
            ),
        ]

        with Session(test_db, expire_on_commit=False) as session:
            session.add_all(inserted_txns)
            session.commit()

        response = test_client.get(f"{self.TRANSACTIONS_API_PATH}/spending-categories")
        assert response.status_code == 200

        body = response.json()
        assert body == ["FOOD_DELIVERY", "GROCERIES"]

    def test_returns_empty_list_when_no_transactions_exist(
        self,
        test_client,
    ):
        response = test_client.get(f"{self.TRANSACTIONS_API_PATH}/spending-categories")
        assert response.status_code == 200
        assert response.json() == []


class TestGetStats:
    STATS_API_PATH = f"{app_config.V1_API_PREFIX}/transactions/stats"

    # def _insert_random_transactions(self, test_db, db_transaction, count: int) -> list:
    #     inserted_txns = [
    #         db_transaction(
    #             transaction_datetime=random_datetime(2025),
    #             user_id=TEST_USER_ID,
    #             dedup_key=random_dedup_key(),
    #         )
    #         for _ in range(count)
    #     ]

    #     with Session(test_db, expire_on_commit=False) as session:
    #         session.add_all(inserted_txns)
    #         session.commit()

    #     return sorted(
    #         inserted_txns,
    #         key=lambda txn: txn.transaction_datetime,
    #         reverse=True,
    #     )


"""

"""
