import datetime as dt
import re
from decimal import Decimal
from uuid import UUID

from currency_converter import CurrencyConverter, ECB_URL, RateNotFoundError

from app.db.transactions import Transaction
from app.project_types import ImportedTransaction

import logging

logger = logging.getLogger(__name__)

# These don't need to be in lowercase anymore. Matching logic is case insensitive now
SUPERMARKET_MERCHANTS = {"barbora", "iki", "lidl", "maxima", "rimi"}
COFFESHOP_MERCHANTS = {
    "caffeine",
    "kavos era",
    "brew. specialty coffee",
    "albas",
    "backstage cafe",
    "caif cafe",
    "caif cafe c1.7",
    "gedimino pr. 10",
    "taste map",
    "uab agerosa",
    "vero cafe",
    "Totorių gatvė",  # Huracan totoriu
}
BUSINESS_LUNCH_MERCHANTS = {
    "aloha",
    "berneliu uzeiga",
    "bernelių užeiga",
    "Ministerija Dienos pietūs",
    "A. Taraškienės firma 3515",
}
STREAMING_MERCHANTS = {"disney", "netflix", "spotify", "youtube"}
FOOD_DELIVERY_MERCHANTS = {"bolt food", "wolt"}
RESTAURANT_MERCHANTS = {
    "Greet.menu",
    "Globaltips",
    "Grill London",
    "ilunch",
    "No Forks Mexican Grill",
    "Spirgis",
    "Wokbusters",
    "Flying Tomato Pizza",
    "JAMMI",
    "Houdini",
    "Holy Donut",
    "Burna House",
    "Asaki",
    "Beigelistai",
    "Desertas Islandijos G3",
    "Jūsų Šnekutis",
}


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
        categorization = get_categorization(transaction)

        new_values = {
            "eur_amount": eur_amount,
            "auto_added": True,
            "job_id": job_id,
            "user_id": user_id,
        }
        enriched_transaction = Transaction.model_validate(
            {**transaction.model_dump(), **new_values, **categorization}
        )

        result.append(enriched_transaction)

    return result


def get_categorization(transaction: ImportedTransaction) -> dict[str, str]:
    if _is_groceries(transaction):
        return {
            "category": "Groceries",
            "sub_category": "Groceries",
            "detail": "Groceries",
        }

    elif _is_breakfast(transaction):
        return {
            "category": "Food & Drink",
            "sub_category": "Food",
            "detail": "Eating Out",
            "meal_type": "Breakfast",
        }

    elif _is_hot_drinks(transaction):
        return {
            "category": "Food & Drink",
            "sub_category": "Food",
            "detail": "Hot Drinks & Snacks",
            "meal_type": "Snacks",
        }

    elif _is_streaming_services(transaction):
        return {
            "category": "Entertainment",
            "sub_category": "Streaming Services",
            "detail": f"{transaction.counterparty} subscription",
        }

    elif _is_business_lunch(transaction):
        return {
            "category": "Food & Drink",
            "sub_category": "Food",
            "detail": "Eating Out",
            "note": "Business Lunch",
            "meal_type": "Lunch",
        }

    elif _is_food_delivery(transaction):
        categorization = {
            "category": "Food & Drink",
            "sub_category": "Food",
            "detail": "Food Delivery",
        }
        hour = transaction.transaction_datetime.hour
        if 10 < hour <= 15:
            meal_type = "Lunch"
        else:
            meal_type = "Dinner"

        categorization["meal_type"] = meal_type
        return categorization

    elif _is_eating_out(transaction):
        categorization = {
            "category": "Food & Drink",
            "sub_category": "Food",
            "detail": "Eating Out",
        }
        hour = transaction.transaction_datetime.hour
        if hour < 11:
            meal_type = "Breakfast"
        elif hour < 17:
            meal_type = "Lunch"
        else:
            meal_type = "Dinner"

        categorization["meal_type"] = meal_type
        return categorization

    return {}


def _is_eating_out(transaction: ImportedTransaction):
    counterparty = transaction.counterparty.lower().strip()
    return any(merchant.lower() in counterparty for merchant in RESTAURANT_MERCHANTS)


def _is_food_delivery(transaction: ImportedTransaction):
    counterparty = transaction.counterparty.lower().strip()
    return any(counterparty == merchant.lower() for merchant in FOOD_DELIVERY_MERCHANTS)


def _is_business_lunch(transaction: ImportedTransaction):
    counterparty = transaction.counterparty.lower().strip()
    return (
        any(counterparty == merchant.lower() for merchant in BUSINESS_LUNCH_MERCHANTS)
        and transaction.transaction_datetime.isoweekday() in range(1, 6)  # Weekday
        and 11 <= transaction.transaction_datetime.hour < 15
    )


def _is_streaming_services(transaction: ImportedTransaction):
    counterparty = transaction.counterparty.lower().strip()
    return any(
        re.search(rf"^{merchant}.*$", counterparty, flags=re.IGNORECASE)
        for merchant in STREAMING_MERCHANTS
    )


def _is_groceries(transaction: ImportedTransaction):
    counterparty = transaction.counterparty.lower().strip()
    return any(counterparty == merchant.lower() for merchant in SUPERMARKET_MERCHANTS)


def _is_breakfast(transaction: ImportedTransaction):
    counterparty = transaction.counterparty.lower().strip()
    return (
        counterparty in ("caffeine", "kavos era")
        and transaction.transaction_datetime.hour < 11
        and transaction.orig_amount > 5
    )


def _is_hot_drinks(transaction: ImportedTransaction):
    counterparty = transaction.counterparty.lower().strip()
    return (
        any(counterparty == merchant.lower() for merchant in COFFESHOP_MERCHANTS)
        and transaction.orig_amount < 5
    )


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
