from decimal import Decimal
import datetime as dt

import pytest

from app.business_rules.spending_categories import (
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
    def test_restaurant_matches(self, importable_transaction, counterparty):
        transaction = importable_transaction(counterparty=counterparty)
        result = eating_out(transaction)

        assert result is not None
        assert result["spending_category"] == "EATING_OUT"

    @pytest.mark.parametrize(
        "counterparty",
        [
            "Caffeine",
            "Kavos Era",
            "backstage cafe",
        ],
    )
    def test_coffeeshop_breakfast_matches(self, importable_transaction, counterparty):
        transaction = importable_transaction(
            counterparty=counterparty,
            transaction_datetime=dt.datetime(2026, 1, 2, 9, 15, 1),
            eur_amount=7.5,
        )
        result = eating_out(transaction)
        assert result is not None
        assert result["spending_category"] == "EATING_OUT"

    def test_amount_too_low_for_breakfast(self, importable_transaction):
        amount = Decimal("5.00")
        transaction = importable_transaction(counterparty="Caffeine", eur_amount=amount)
        result = eating_out(transaction)

        assert result is None

    def test_timestamp_too_late_for_breakfast(self, importable_transaction):
        amount = Decimal("8.00")
        timestamp = dt.datetime.fromisoformat("2026-01-10T11:25:10")
        transaction = importable_transaction(
            counterparty="Caffeine", transaction_datetime=timestamp, eur_amount=amount
        )
        result = eating_out(transaction)

        assert result is None

    def test_no_counterparty_match(self, importable_transaction):
        transaction = importable_transaction(counterparty="Lemon Gym")
        result = eating_out(transaction)

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
    def test_positive_matches(self, importable_transaction, counterparty):
        transaction = importable_transaction(counterparty=counterparty)
        result = food_delivery(transaction)

        assert result is not None
        assert result["spending_category"] == "FOOD_DELIVERY"

    @pytest.mark.parametrize(
        "counterparty",
        [
            "Bolt",
            "Maxima",
        ],
    )
    def test_no_match(self, importable_transaction, counterparty):
        transaction = importable_transaction(counterparty=counterparty)
        result = food_delivery(transaction)

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
    def test_positive_matches(self, importable_transaction, counterparty):
        transaction = importable_transaction(counterparty=counterparty)
        result = streaming_services(transaction)

        assert result is not None
        assert result["spending_category"] == "STREAMING_SERVICES"

    def test_no_match(self, importable_transaction):
        transaction = importable_transaction(counterparty="Lidl")
        result = streaming_services(transaction)

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
    def test_positive_matches(self, importable_transaction, counterparty):
        transaction = importable_transaction(counterparty=counterparty)
        result = groceries(transaction)

        assert result is not None
        assert result["spending_category"] == "GROCERIES"

    def test_no_match(
        self,
        importable_transaction,
    ):
        transaction = importable_transaction(counterparty="Random express")
        result = groceries(transaction)

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
    def test_positive_matches(self, importable_transaction, counterparty):
        transaction = importable_transaction(counterparty=counterparty)
        result = shopping_clothes(transaction)

        assert result is not None
        assert result["spending_category"] == "SHOPPING_CLOTHES"

    @pytest.mark.parametrize(
        "counterparty",
        [
            "Elsen",
            "Amazon",
        ],
    )
    def test_no_match(self, importable_transaction, counterparty):
        transaction = importable_transaction(counterparty=counterparty)
        result = shopping_clothes(transaction)

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
    def test_positive_matches(self, importable_transaction, counterparty):
        transaction = importable_transaction(counterparty=counterparty)
        result = shopping_other(transaction)

        assert result is not None
        assert result["spending_category"] == "SHOPPING_OTHER"

    @pytest.mark.parametrize(
        "counterparty",
        [
            "Zara",
            "Apranga group",
        ],
    )
    def test_no_match(self, importable_transaction, counterparty):
        transaction = importable_transaction(counterparty=counterparty)
        result = shopping_other(transaction)

        assert result is None


class TestGymMembership:
    @pytest.mark.parametrize(
        "counterparty",
        [
            "lemon gym",  # Lowercase
            "Lemon Gym",  # Title case
        ],
    )
    def test_positive_matches(self, importable_transaction, counterparty):
        transaction = importable_transaction(counterparty=counterparty)
        result = gym_membership(transaction)

        assert result is not None
        assert result["spending_category"] == "GYM"

    def test_no_match(self, importable_transaction):
        transaction = importable_transaction(counterparty="Other value")
        result = gym_membership(transaction)

        assert result is None


class TestLandlordPayment:
    def test_wrong_counterparty(self, importable_transaction):
        transaction = importable_transaction(
            counterparty="Jonas Johnsson", eur_amount=Decimal("15.00")
        )
        result = landlord_payment(transaction)

        assert result is None

    def test_utilities_payment_amount(self, importable_transaction):
        transaction = importable_transaction(
            counterparty="Aušra Adelė Vaišvilė", eur_amount=Decimal("100.50")
        )
        result = landlord_payment(transaction)

        assert result is not None
        assert result["spending_category"] == "RENT_UTILITIES"

    def test_rent_payment_amount(self, importable_transaction):
        transaction = importable_transaction(
            counterparty="Aušra Adelė Vaišvilė", eur_amount=Decimal("550.12")
        )
        result = landlord_payment(transaction)

        assert result is not None
        assert result["spending_category"] == "RENT"


class TestHotDrinks:
    @pytest.mark.parametrize(
        "counterparty",
        [
            "Caffeine",
            "UAB agerosa",
            "totorių gatvė",
        ],
    )
    def test_positive_matches(self, importable_transaction, counterparty):
        eligible_amount = Decimal("3.50")
        transaction = importable_transaction(
            counterparty=counterparty, eur_amount=eligible_amount
        )
        result = hot_drinks(transaction)

        assert result is not None
        assert result["spending_category"] == "CAFE_SNACKS"

    def test_wrong_counterparty(self, importable_transaction):
        transaction = importable_transaction(
            counterparty="Maxima", eur_amount=Decimal("3.50")
        )
        result = hot_drinks(transaction)

        assert result is None

    def test_amount_too_high(self, importable_transaction):
        amount = Decimal("5.50")
        transaction = importable_transaction(counterparty="Caffeine", eur_amount=amount)
        result = hot_drinks(transaction)

        assert result is None
