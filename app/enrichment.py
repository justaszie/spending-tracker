import datetime as dt
from decimal import Decimal
from typing import Sequence
from uuid import UUID

from currency_converter import CurrencyConverter, ECB_URL, RateNotFoundError

from app.db.transactions import Transaction
from app.project_types import ImportedTransaction

import logging

from app.category_rules import CategoryData, CATEGORY_RULES, CategoryRuleFunction

logger = logging.getLogger(__name__)


def enrich_transactions(
    transactions: list[ImportedTransaction], job_id: UUID, user_id: UUID
) -> list[Transaction]:
    result = []
    converter = CurrencyConverter(ECB_URL)
    for transaction in transactions:
        # 1. convert to eur
        try:
            eur_amount = get_eur_amount(
                converter,
                transaction.transaction_datetime,
                transaction.orig_currency,
                transaction.orig_amount,
            )
        # If there are issues with the converter module, we use null eur amount
        except Exception:
            eur_amount = None

        if eur_amount is None:
            logger.log(logging.WARNING, f"Could not convert to EUR for {transaction}")

        # 2. Calculate spending categories
        category_values = get_category_data(transaction, CATEGORY_RULES)




        new_values = {
            "eur_amount": eur_amount,
            "manually_added": False,
            "job_id": job_id,
            "user_id": user_id,
        }

        enriched_transaction = {
            **transaction.model_dump(),
            **new_values,
            **category_values,
        }

        if is_food_spending(category_values):
            enriched_transaction["meal_type"] = get_meal_type(transaction, category_values)

        result.append(Transaction.model_validate(enriched_transaction))

    return result

def is_food_spending(category_values: CategoryData) -> bool:
    return category_values.get("l2_category") == "Food"

def get_category_data(
    transaction: ImportedTransaction, rules: Sequence[CategoryRuleFunction]
) -> CategoryData:
    # Input: standardized transaction object
    # Ouput: category data dictionary. Empty dictionary if no data to return (no rule aplies)

    # Rule selection policy:
    # We take the results of the first category rule that returns value
    for rule_fn in rules:
        category_values = rule_fn(transaction)
        if category_values:
            return category_values

    return {}


def get_meal_type(transaction: ImportedTransaction, category_values: CategoryData) -> str | None:

    if category_values.get("l3_category") == "Hot Drinks & Snacks":
        return "Snacks"

    hour = transaction.transaction_datetime.hour
    if hour < 11:
        return "Breakfast"
    elif hour < 17:
        return "Lunch"
    else:
        return "Dinner"


def get_eur_amount(
    converter: CurrencyConverter,
    txn_date: dt.date,
    orig_currency: str,
    orig_amount: Decimal,
) -> Decimal | None:
    MAX_RETRIES = 10

    if orig_currency.upper() == "EUR":
        return orig_amount

    eur_amount = None
    exchange_rate_date = txn_date
    retry_attempts = 0
    # If the rate on the day of the transaction is not available
    # we find the rate for the closest date
    while eur_amount is None:
        if retry_attempts > MAX_RETRIES:
            return None

        try:
            eur_amount = converter.convert(
                orig_amount, orig_currency, "EUR", date=exchange_rate_date
            )
        except RateNotFoundError:
            exchange_rate_date = exchange_rate_date - dt.timedelta(days=1)
            retry_attempts += 1

    return Decimal(eur_amount).quantize(Decimal("0.01"))
