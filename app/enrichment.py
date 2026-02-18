from collections.abc import Sequence
from decimal import Decimal
import datetime as dt
import logging

from currency_converter import CurrencyConverter, RateNotFoundError

from app.business_rules.spending_categories import (
    CategoryData,
    CategoryRuleFunction,
    get_category_rules,
)
from app.core.project_types import ExtractedTransaction

logger = logging.getLogger(__name__)


class CurrencyConversionError(Exception):
    pass

# TODO - refactor to use ImportableTransaction and get rid of extra eur_amount param
def get_category_data(
    transaction: ExtractedTransaction,
    eur_amount: Decimal,
    category_rules: Sequence[CategoryRuleFunction] | None = None,
) -> CategoryData:
    # Input: standardized transaction object
    # Ouput: category data dictionary. Empty dictionary if no rule applies

    # Rule selection policy:
    # We take the results of the first category rule that returns value
    category_rules = category_rules or get_category_rules()
    for rule_fn in category_rules:
        category_values = rule_fn(transaction, eur_amount)
        if category_values:
            return category_values

    return {}


def is_food_spending(category_values: CategoryData) -> bool:
    return category_values.get("l2_category") == "Food"


def get_meal_type(
    transaction: ExtractedTransaction, category_values: CategoryData
) -> str | None:
    if not is_food_spending(category_values=category_values):
        return None

    if category_values.get("l3_category") == "Hot Drinks & Snacks":
        return "Snacks"

    hour = transaction.transaction_datetime.hour
    if hour < 11:
        return "Breakfast"
    if hour < 17:
        return "Lunch"
    return "Dinner"


def get_eur_amount(
    converter: CurrencyConverter,
    txn_date: dt.date,
    orig_currency: str,
    orig_amount: Decimal,
) -> Decimal:
    max_retries = 10

    if orig_currency.upper() == "EUR":
        return orig_amount

    eur_amount = None
    exchange_rate_date = txn_date
    retry_attempts = 0
    # If the rate on the day of the transaction is not available
    # we find the rate for the closest date
    while eur_amount is None:
        if retry_attempts > max_retries:
            raise CurrencyConversionError(
                "EUR conversion is not working - max per-txn attempts breached"
            )

        try:
            eur_amount = converter.convert(
                orig_amount, orig_currency, "EUR", date=exchange_rate_date
            )
        except RateNotFoundError:
            exchange_rate_date = exchange_rate_date - dt.timedelta(days=1)
            retry_attempts += 1
        except Exception as e:
            raise CurrencyConversionError(f"EUR conversion is not working: {e}") from e

    return Decimal(eur_amount).quantize(Decimal("0.01"))
