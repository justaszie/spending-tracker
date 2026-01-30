# This module contains definition of categorization rules
from collections.abc import Callable
from decimal import Decimal
import re
from typing import NotRequired, TypedDict

from app.project_types import ImportedTransaction


class CategoryData(TypedDict):
    l1_category: NotRequired[str]
    l2_category: NotRequired[str]
    l3_category: NotRequired[str]
    note: NotRequired[str]


# Design of category rule functions:
# Input: standardized transaction object, standard_ccy_amount (e.g. EUR) for amount-based rules
# Output: Category data dictionary if rule definition matches transaction. None if it doesn't match
type CategoryRuleFunction = Callable[
    [ImportedTransaction, Decimal], CategoryData | None
]

# These don't need to be in lowercase anymore. Matching logic is case insensitive now
SUPERMARKET_MERCHANTS = {"barbora", "iki", "lidl", "maxima", "rimi", "narvesen"}
COFFESHOP_MERCHANTS = {
    "caffeine",
    "kavos era",
    "brew. specialty coffee",
    "baristokrat specialty coffee",
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
    "Senolių tradicija",
}

STREAMING_MERCHANTS = ("disney", "netflix", "spotify", "youtube")
STREAMING_PATTERNS = tuple(
    re.compile(f"^.*{pattern}.*$", re.IGNORECASE) for pattern in STREAMING_MERCHANTS
)
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

ECOM_MERCHANTS = (
    r".*amazon(?:\s.*)?$",
    r"pigu(?:\.|\s)lt",
    r"varle",
)
ECOM_MERCHANT_PATTERNS = tuple(
    re.compile(pattern, re.IGNORECASE) for pattern in ECOM_MERCHANTS
)

CLOTHES_SHOPPING_MERCHANTS = (r"zalando", r"zara", r"h&m")
CLOTHES_SHOPPING_PATTERNS = tuple(
    re.compile(pattern, re.IGNORECASE) for pattern in CLOTHES_SHOPPING_MERCHANTS
)

GYM_MEMBERSHIP_PATTERNS = tuple(
    re.compile(pattern, re.IGNORECASE) for pattern in (r"lemon gym",)
)


### RULE DEFINITIONS
def eating_out(
    transaction: ImportedTransaction, standard_ccy_amount: Decimal
) -> CategoryData | None:
    counterparty = transaction.counterparty.lower().strip()
    if any(merchant.lower() in counterparty for merchant in RESTAURANT_MERCHANTS):
        return {
            "l1_category": "Food & Drink",
            "l2_category": "Food",
            "l3_category": "Eating Out",
        }
    return None


def food_delivery(
    transaction: ImportedTransaction, standard_ccy_amount: Decimal
) -> CategoryData | None:
    counterparty = transaction.counterparty.lower().strip()
    if any(counterparty == merchant.lower() for merchant in FOOD_DELIVERY_MERCHANTS):
        return {
            "l1_category": "Food & Drink",
            "l2_category": "Food",
            "l3_category": "Food Delivery",
        }
    return None


def business_lunch(
    transaction: ImportedTransaction, standard_ccy_amount: Decimal
) -> CategoryData | None:
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


def streaming_services(
    transaction: ImportedTransaction, standard_ccy_amount: Decimal
) -> CategoryData | None:
    counterparty = transaction.counterparty.lower().strip()
    if any(pattern.search(counterparty) is not None for pattern in STREAMING_PATTERNS):
        return {
            "l1_category": "Entertainment",
            "l2_category": "Streaming Services",
            "l3_category": f"{transaction.counterparty} subscription",
        }
    return None


def groceries(
    transaction: ImportedTransaction, standard_ccy_amount: Decimal
) -> CategoryData | None:
    counterparty = transaction.counterparty.lower().strip()
    if any(counterparty == merchant.lower() for merchant in SUPERMARKET_MERCHANTS):
        return {
            "l1_category": "Groceries",
            "l2_category": "Groceries",
            "l3_category": "Groceries",
        }
    return None


def breakfast(
    transaction: ImportedTransaction, standard_ccy_amount: Decimal
) -> CategoryData | None:
    counterparty = transaction.counterparty.lower().strip()
    if (
        counterparty in COFFESHOP_MERCHANTS
        and transaction.transaction_datetime.hour < 11
        and standard_ccy_amount > 5
    ):
        return {
            "l1_category": "Food & Drink",
            "l2_category": "Food",
            "l3_category": "Eating Out",
        }
    return None


def hot_drinks(
    transaction: ImportedTransaction, standard_ccy_amount: Decimal
) -> CategoryData | None:
    counterparty = transaction.counterparty.lower().strip()
    if (
        any(counterparty == merchant.lower() for merchant in COFFESHOP_MERCHANTS)
        and standard_ccy_amount < 5
    ):
        return {
            "l1_category": "Food & Drink",
            "l2_category": "Food",
            "l3_category": "Hot Drinks & Snacks",
        }
    return None


def landlord_payment(
    transaction: ImportedTransaction, standard_ccy_amount: Decimal
) -> CategoryData | None:
    to_landlord = transaction.counterparty.upper() == "AUŠRA ADELĖ VAIŠVILĖ"
    if not to_landlord:
        return None

    if standard_ccy_amount >= 400:
        return {
            "l1_category": "Rent",
            "l2_category": "Rent",
            "l3_category": "Rent",
        }

    return {
        "l1_category": "Rent",
        "l2_category": "Utilities",
        "l3_category": "Utilities",
    }


def shopping_clothes(
    transaction: ImportedTransaction, standard_ccy_amount: Decimal
) -> CategoryData | None:
    if any(
        pattern.search(transaction.counterparty) is not None
        for pattern in CLOTHES_SHOPPING_PATTERNS
    ):
        return {
            "l1_category": "Shopping",
            "l2_category": "Clothes",
            "l3_category": "Clothes",
        }

    return None


def shopping_other(
    transaction: ImportedTransaction, standard_ccy_amount: Decimal
) -> CategoryData | None:
    if any(
        pattern.search(transaction.counterparty) is not None
        for pattern in ECOM_MERCHANT_PATTERNS
    ):
        return {
            "l1_category": "Shopping",
        }

    return None


def gym_membership(
    transaction: ImportedTransaction, standard_ccy_amount: Decimal
) -> CategoryData | None:
    if any(
        pattern.search(transaction.counterparty) is not None
        for pattern in GYM_MEMBERSHIP_PATTERNS
    ):
        return {
            "l1_category": "Health",
            "l2_category": "Gym",
            "l3_category": "Gym",
        }

    return None


# For now, the list of specific categorization rules is setup manually
CATEGORY_RULES: list[CategoryRuleFunction] = [
    streaming_services,
    groceries,
    breakfast,
    hot_drinks,
    business_lunch,
    eating_out,
    food_delivery,
    landlord_payment,
    shopping_clothes,
    shopping_other,
    gym_membership,
]
