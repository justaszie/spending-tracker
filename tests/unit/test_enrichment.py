from decimal import Decimal
import datetime as dt

from currency_converter import RateNotFoundError
import pytest

from app.business_rules.spending_categories import breakfast, groceries, hot_drinks
from app.enrichment import (
    CurrencyConversionError,
    get_category_data,
    get_eur_amount,
    get_meal_type,
)


class TestMealType:
    def test_matches_snacks(self, importable_transaction):
        transaction = importable_transaction(
            l2_category="Food", l3_category="Hot Drinks & Snacks"
        )
        assert get_meal_type(transaction) == "Snacks"

    def test_returns_breakfast_for_morning(self, importable_transaction):
        transaction = importable_transaction(
            l2_category="Food",
            l3_category="Eating Out",
            transaction_datetime=dt.datetime(2026, 1, 10, 10, 0, 0),
        )
        assert get_meal_type(transaction) == "Breakfast"

    def test_returns_lunch_for_lunch_period(self, importable_transaction):
        transaction = importable_transaction(
            l2_category="Food",
            l3_category="Eating Out",
            transaction_datetime=dt.datetime(2026, 1, 10, 11, 0, 0),
        )
        assert get_meal_type(transaction) == "Lunch"
        transaction_16 = importable_transaction(
            l2_category="Food",
            l3_category="Eating Out",
            transaction_datetime=dt.datetime(2026, 1, 10, 16, 59, 0),
        )
        assert get_meal_type(transaction_16) == "Lunch"

    def test_returns_dinner_for_evening(self, importable_transaction):
        transaction = importable_transaction(
            l2_category="Food",
            l3_category="Eating Out",
            transaction_datetime=dt.datetime(2026, 1, 10, 17, 0, 0),
        )
        assert get_meal_type(transaction) == "Dinner"

    def test_returns_none_when_not_food(self, importable_transaction):
        transaction = importable_transaction(
            l2_category="Groceries", l3_category="Groceries"
        )
        assert get_meal_type(transaction) is None


class TestGetEurAmount:
    @pytest.fixture
    def converter(self, mocker):
        return mocker.Mock()

    def test_return_same_amount_when_eur(self, converter):
        amount = Decimal("42.99")
        txn_date = dt.date(2026, 1, 11)
        result = get_eur_amount(converter, txn_date, "EUR", amount)
        assert result == amount
        converter.convert.assert_not_called()

    def test_converts_non_eur(self, converter):
        converter.convert.return_value = 101.22255
        txn_date = dt.date(2026, 1, 11)
        expected = Decimal("101.22")
        actual = get_eur_amount(converter, txn_date, "GBP", Decimal("15.55"))
        assert expected == actual

    def test_raises_exc_after_10_rate_not_found_retries(self, converter):
        converter.convert.side_effect = RateNotFoundError()
        max_retries = 10
        txn_date = dt.date(2026, 1, 11)
        with pytest.raises(CurrencyConversionError):
            get_eur_amount(converter, txn_date, "GBP", Decimal("10"))
        assert converter.convert.call_count == 1 + max_retries

    def test_tries_fallback_dates(self, converter):
        def fail_first_two_dates(*_args, **kwargs):
            if kwargs["date"] in [txn_date, txn_date - dt.timedelta(days=1)]:
                raise RateNotFoundError()

            return 75.6

        txn_date = dt.date(2026, 1, 1)

        converter.convert.side_effect = fail_first_two_dates
        result = get_eur_amount(converter, txn_date, "GBP", Decimal("70"))

        assert result == Decimal("75.6")
        assert converter.convert.call_count == 3

    def test_maps_exceptions_to_standard(self, converter):
        converter.convert.side_effect = ValueError("no internet")
        txn_date = dt.date(2026, 1, 11)
        with pytest.raises(CurrencyConversionError) as excinfo:
            get_eur_amount(converter, txn_date, "GBP", Decimal("10"))
        assert excinfo.value.__cause__ is converter.convert.side_effect


class TestGetCategories:
    def test_uses_first_matching_rule(self, importable_transaction):
        # 3 active rules, 2nd one applies
        test_rules = [groceries, hot_drinks, breakfast]
        transaction = importable_transaction(counterparty="Caffeine", eur_amount=5)
        result = get_category_data(transaction, test_rules)
        assert result["l1_category"] == "Food & Drinks"
        assert result["l2_category"] == "Food"
        assert result["l3_category"] == "Hot Drinks & Snacks"

    def test_first_rule_wins_when_multiple_match(self, importable_transaction):
        def first_rule(_):
            return {"l1_category": "First"}

        def second_rule(_):
            return {"l1_category": "Second"}

        transaction = importable_transaction()
        result = get_category_data(
            transaction, category_rules=[first_rule, second_rule]
        )
        assert result == {"l1_category": "First"}

    def test_returns_empty_when_no_rule_applies(self, importable_transaction):
        transaction = importable_transaction(
            counterparty="Unknown Merchant", eur_amount=10
        )
        result = get_category_data(transaction, category_rules=[groceries, hot_drinks])
        assert result == {}

    def test_uses_default_rules_when_none_provided(
        self, importable_transaction, mocker
    ):
        def stub_rule(_):
            return {"l1_category": "X"}

        mocker.patch("app.enrichment.get_category_rules", return_value=[stub_rule])
        transaction = importable_transaction()
        result = get_category_data(transaction)
        assert result == {"l1_category": "X"}

    def test_returns_empty_when_rules_empty_list(self, importable_transaction):
        transaction = importable_transaction()
        result = get_category_data(transaction, category_rules=[])
        assert result == {}
