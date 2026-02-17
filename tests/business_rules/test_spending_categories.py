from decimal import Decimal
import datetime as dt

import pytest

from app.business_rules.spending_categories import (
    breakfast,
    business_lunch,
    eating_out,
    food_delivery,
    groceries,
    gym_membership,
    hot_drinks,
    landlord_payment,
    shopping_clothes,
    shopping_other,
    streaming_services,
)


@pytest.fixture(scope="module")
def sample_amount():
    return Decimal("15.00")


class TestEatingOut:
    @pytest.mark.parametrize(
        "counterparty",
        [
            "GReet.menu",  # Mixed case
            "greet.menu",  # Lowercase
            "GRILL LONDON",
            "Wokbusters",
        ],
    )
    def test_positive_matches(self, extracted_transaction, counterparty, sample_amount):
        transaction = extracted_transaction(counterparty=counterparty)
        result = eating_out(transaction, sample_amount)

        assert result is not None
        assert result["l1_category"] == "Food & Drinks"
        assert result["l2_category"] == "Food"
        assert result["l3_category"] == "Eating Out"

    def test_no_match(self, extracted_transaction, sample_amount):
        transaction = extracted_transaction(counterparty="Lemon Gym")
        result = eating_out(transaction, sample_amount)

        assert result is None


class TestFoodDelivery:
    @pytest.mark.parametrize(
        "counterparty",
        [
            "bolt food",  # Lowercase
            "BOLT FOOD",  # Uppercase
            "Wolt",
        ],
    )
    def test_positive_matches(self, extracted_transaction, counterparty, sample_amount):
        transaction = extracted_transaction(counterparty=counterparty)
        result = food_delivery(transaction, sample_amount)

        assert result is not None
        assert result["l1_category"] == "Food & Drinks"
        assert result["l2_category"] == "Food"
        assert result["l3_category"] == "Food Delivery"

    @pytest.mark.parametrize(
        "counterparty",
        [
            "Bolt",
            "Maxima",
        ],
    )
    def test_no_match(self, extracted_transaction, counterparty, sample_amount):
        transaction = extracted_transaction(counterparty=counterparty)
        result = food_delivery(transaction, sample_amount)

        assert result is None


class TestStreamingServices:
    @pytest.mark.parametrize(
        "counterparty",
        [
            "Disney+",  # Mixed case
            "disney+",  # Lowercase
            "Netflix subscription",
            "Spotify Premium",
        ],
    )
    def test_positive_matches(self, extracted_transaction, counterparty, sample_amount):
        transaction = extracted_transaction(counterparty=counterparty)
        result = streaming_services(transaction, sample_amount)

        assert result is not None
        assert result["l1_category"] == "Entertainment"
        assert result["l2_category"] == "Streaming Services"
        assert result["l3_category"] == f"{counterparty} subscription"

    def test_no_match(self, extracted_transaction, sample_amount):
        transaction = extracted_transaction(counterparty="Lidl")
        result = streaming_services(transaction, sample_amount)

        assert result is None


class TestGroceries:
    @pytest.mark.parametrize(
        "counterparty",
        [
            "barbora",  # Lowercase
            "Barbora",  # Title case
            "iki",
            "lidl",
        ],
    )
    def test_positive_matches(self, extracted_transaction, counterparty, sample_amount):
        transaction = extracted_transaction(counterparty=counterparty)
        result = groceries(transaction, sample_amount)

        assert result is not None
        assert result["l1_category"] == "Groceries"
        assert result["l2_category"] == "Groceries"
        assert result["l3_category"] == "Groceries"

    def test_no_match(
        self,
        extracted_transaction,
        sample_amount,
    ):
        transaction = extracted_transaction(counterparty="Random express")
        result = groceries(transaction, sample_amount)

        assert result is None


class TestShoppingClothes:
    @pytest.mark.parametrize(
        "counterparty",
        [
            "zalando",  # Lowercase
            "ZALANDO",  # Uppercase
            "zara",
            "H&M",
        ],
    )
    def test_positive_matches(self, extracted_transaction, counterparty, sample_amount):
        transaction = extracted_transaction(counterparty=counterparty)
        result = shopping_clothes(transaction, sample_amount)

        assert result is not None
        assert result["l1_category"] == "Shopping"
        assert result["l2_category"] == "Clothes"
        assert result["l3_category"] == "Clothes"

    @pytest.mark.parametrize(
        "counterparty",
        [
            "Elsen",
            "Amazon",
        ],
    )
    def test_no_match(self, extracted_transaction, counterparty, sample_amount):
        transaction = extracted_transaction(counterparty=counterparty)
        result = shopping_clothes(transaction, sample_amount)

        assert result is None


class TestShoppingOther:
    @pytest.mark.parametrize(
        "counterparty",
        [
            "amazon",  # Lowercase
            "AMAZON",  # Uppercase
            "Pigu.lt",
            "varle",
        ],
    )
    def test_positive_matches(self, extracted_transaction, counterparty, sample_amount):
        transaction = extracted_transaction(counterparty=counterparty)
        result = shopping_other(transaction, sample_amount)

        assert result is not None
        assert result["l1_category"] == "Shopping"

    @pytest.mark.parametrize(
        "counterparty",
        [
            "Zara",
            "Apranga group",
        ],
    )
    def test_no_match(self, extracted_transaction, counterparty, sample_amount):
        transaction = extracted_transaction(counterparty=counterparty)
        result = shopping_other(transaction, sample_amount)

        assert result is None


class TestGymMembership:
    @pytest.mark.parametrize(
        "counterparty",
        [
            "lemon gym",  # Lowercase
            "Lemon Gym",  # Title case
        ],
    )
    def test_positive_matches(self, extracted_transaction, counterparty, sample_amount):
        transaction = extracted_transaction(counterparty=counterparty)
        result = gym_membership(transaction, sample_amount)

        assert result is not None
        assert result["l1_category"] == "Health"
        assert result["l2_category"] == "Gym"
        assert result["l3_category"] == "Gym"

    def test_no_match(self, extracted_transaction, sample_amount):
        transaction = extracted_transaction(counterparty="Other value")
        result = gym_membership(transaction, sample_amount)

        assert result is None


class TestLandlordPayment:
    def test_wrong_counterparty(self, extracted_transaction, sample_amount):
        transaction = extracted_transaction(counterparty="Jonas Johnsson")
        result = landlord_payment(transaction, sample_amount)

        assert result is None

    def test_rent_payment_amount(self, extracted_transaction):
        transaction = extracted_transaction(counterparty="Aušra Adelė Vaišvilė")
        result = landlord_payment(transaction, Decimal("100.50"))

        assert result["l1_category"] == "Rent"
        assert result["l2_category"] == "Utilities"
        assert result["l3_category"] == "Utilities"

    def test_utilities_payment_amount(self, extracted_transaction):
        transaction = extracted_transaction(counterparty="Aušra Adelė Vaišvilė")
        result = landlord_payment(transaction, Decimal("550.12"))

        assert result["l1_category"] == "Rent"
        assert result["l2_category"] == "Rent"
        assert result["l3_category"] == "Rent"


class TestHotDrinks:
    @pytest.mark.parametrize(
        "counterparty",
        [
            "Caffeine",
            "UAB agerosa",
            "totorių gatvė",
        ],
    )
    def test_positive_matches(self, extracted_transaction, counterparty):
        eligible_amount = Decimal("3.50")
        transaction = extracted_transaction(counterparty=counterparty)
        result = hot_drinks(transaction, eligible_amount)

        assert result["l1_category"] == "Food & Drinks"
        assert result["l2_category"] == "Food"
        assert result["l3_category"] == "Hot Drinks & Snacks"

    def test_wrong_counterparty(self, extracted_transaction):
        transaction = extracted_transaction(counterparty="Maxima")
        result = hot_drinks(transaction, Decimal("3.50"))

        assert result is None

    def test_amount_too_high(self, extracted_transaction):
        amount = Decimal("5.50")
        transaction = extracted_transaction(counterparty="Caffeine")
        result = hot_drinks(transaction, amount)

        assert result is None


class TestBreakfast:
    @pytest.mark.parametrize(
        "counterparty",
        [
            "Caffeine",
            "Kavos Era",
            "backstage cafe",
        ],
    )
    def test_positive_matches(self, extracted_transaction, counterparty):
        eligible_amount = Decimal("6.50")
        timestamp = dt.datetime.fromisoformat("2026-01-10T10:30:10")
        transaction = extracted_transaction(
            counterparty=counterparty, transaction_datetime=timestamp
        )
        result = breakfast(transaction, eligible_amount)

        assert result["l1_category"] == "Food & Drinks"
        assert result["l2_category"] == "Food"
        assert result["l3_category"] == "Eating Out"

    def test_wrong_counterparty(self, extracted_transaction):
        transaction = extracted_transaction(counterparty="Maxima")
        result = breakfast(transaction, Decimal("3.50"))

        assert result is None

    def test_amount_too_low(self, extracted_transaction):
        amount = Decimal("5.00")
        transaction = extracted_transaction(counterparty="Caffeine")
        result = breakfast(transaction, amount)

        assert result is None

    def test_timestamp_too_late(self, extracted_transaction):
        amount = Decimal("8.00")
        timestamp = dt.datetime.fromisoformat("2026-01-10T11:25:10")
        transaction = extracted_transaction(
            counterparty="Caffeine", transaction_datetime=timestamp
        )
        result = breakfast(transaction, amount)

        assert result is None


class TestBusinessLunch:
    @pytest.mark.parametrize(
        ("counterparty", "iso_timestamp"),
        [
            ("Senolių kepyklėlė", "2026-02-16T11:30:10"),  # Monday
            ("ministerija dienos pietūs", "2026-02-11T13:30:10"),  # Wednesday
            ("bernelių užeiga", "2026-02-13T14:15:00"),  # Friday
        ],
    )
    def test_positive_matches(self, extracted_transaction, counterparty, iso_timestamp, sample_amount):
        timestamp = dt.datetime.fromisoformat(iso_timestamp)
        transaction = extracted_transaction(
            counterparty=counterparty, transaction_datetime=timestamp
        )
        result = business_lunch(transaction, sample_amount)

        assert result["l1_category"] == "Food & Drinks"
        assert result["l2_category"] == "Food"
        assert result["l3_category"] == "Eating Out"

    def test_wrong_counterparty(self, extracted_transaction, sample_amount):
        transaction = extracted_transaction(counterparty="Maxima")
        result = business_lunch(transaction, sample_amount)

        assert result is None


    @pytest.mark.parametrize(
        "iso_timestamp",
        [
            "2026-02-14T14:15:00",
            "2026-02-15T12:15:00"
        ]
    )
    def test_weekend_no_match(self, extracted_transaction, iso_timestamp, sample_amount):
        timestamp = dt.datetime.fromisoformat(iso_timestamp)
        transaction = extracted_transaction(
            counterparty="Senolių kepyklėlė", transaction_datetime=timestamp
        )
        result = business_lunch(transaction, sample_amount)

        assert result is None

    def test_after_lunch_hours(self, extracted_transaction, sample_amount):
        timestamp = dt.datetime.fromisoformat("2026-02-16T16:15:15")
        transaction = extracted_transaction(
            counterparty="Senolių kepyklėlė", transaction_datetime=timestamp
        )
        result = business_lunch(transaction, sample_amount)

        assert result is None



