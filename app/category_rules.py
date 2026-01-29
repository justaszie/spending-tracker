# This module contains definition of categorization rules
import re
from typing import Callable, NotRequired, TypedDict

from app.project_types import ImportedTransaction


class CategoryData(TypedDict):
    l1_category: NotRequired[str]
    l2_category: NotRequired[str]
    l3_category: NotRequired[str]
    note: NotRequired[str]


# Design of category rule functions:
# Input: standardized transactio object
# Output: Category data dictionary if rule definition matches transaction. None if it doesn't match
type CategoryRuleFunction = Callable[[ImportedTransaction], CategoryData | None]

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


### RULE DEFINITIONS
def _is_eating_out(transaction: ImportedTransaction) -> CategoryData | None:
    counterparty = transaction.counterparty.lower().strip()
    if any(merchant.lower() in counterparty for merchant in RESTAURANT_MERCHANTS):
        return {
            "l1_category": "Food & Drink",
            "l2_category": "Food",
            "l3_category": "Eating Out",
        }
    return None


def _is_food_delivery(transaction: ImportedTransaction) -> CategoryData | None:
    counterparty = transaction.counterparty.lower().strip()
    if any(counterparty == merchant.lower() for merchant in FOOD_DELIVERY_MERCHANTS):
        return {
            "l1_category": "Food & Drink",
            "l2_category": "Food",
            "l3_category": "Food Delivery",
        }
    return None


def _is_business_lunch(transaction: ImportedTransaction) -> CategoryData | None:
    counterparty = transaction.counterparty.lower().strip()
    if (
        any(counterparty == merchant.lower() for merchant in BUSINESS_LUNCH_MERCHANTS)
        and transaction.transaction_datetime.isoweekday() in range(1, 6)  # Weekday
        and 11 <= transaction.transaction_datetime.hour < 15
    ):
        return {
            "l1_category": "Food & Drink",
            "l2_category": "Food",
            "l3_category": "Eating Out",
            "note": "Business Lunch",
        }
    return None


def _is_streaming_services(transaction: ImportedTransaction) -> CategoryData | None:
    counterparty = transaction.counterparty.lower().strip()
    if any(
        re.search(rf"^{merchant}.*$", counterparty, flags=re.IGNORECASE)
        for merchant in STREAMING_MERCHANTS
    ):
        return {
            "l1_category": "Entertainment",
            "l2_category": "Streaming Services",
            "l3_category": f"{transaction.counterparty} subscription",
        }
    return None


def _is_groceries(transaction: ImportedTransaction) -> CategoryData | None:
    counterparty = transaction.counterparty.lower().strip()
    if any(counterparty == merchant.lower() for merchant in SUPERMARKET_MERCHANTS):
        return {
            "l1_category": "Groceries",
            "l2_category": "Groceries",
            "l3_category": "Groceries",
        }
    return None


def _is_breakfast(transaction: ImportedTransaction) -> CategoryData | None:
    counterparty = transaction.counterparty.lower().strip()
    if (
        counterparty in ("caffeine", "kavos era")
        and transaction.transaction_datetime.hour < 11
        and transaction.orig_amount > 5
    ):
        return {
            "l1_category": "Food & Drink",
            "l2_category": "Food",
            "l3_category": "Eating Out",
        }
    return None


def _is_hot_drinks(transaction: ImportedTransaction) -> CategoryData | None:
    counterparty = transaction.counterparty.lower().strip()
    if (
        any(counterparty == merchant.lower() for merchant in COFFESHOP_MERCHANTS)
        and transaction.orig_amount < 5
    ):
        return {
            "l1_category": "Food & Drink",
            "l2_category": "Food",
            "l3_category": "Hot Drinks & Snacks",
        }
    return None


# For now, the list of specific categorization rules is setup manually
CATEGORY_RULES: list[CategoryRuleFunction] = [
    _is_streaming_services,
    _is_groceries,
    _is_breakfast,
    _is_hot_drinks,
    _is_business_lunch,
    _is_eating_out,
    _is_food_delivery,
]
