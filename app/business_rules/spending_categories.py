# This module contains definition of categorization rules
from collections.abc import Callable
from typing import Literal, NotRequired, TypedDict
import re

from app.core.project_types import ImportableTransaction

# Canonical spending category values (mapping sheet: "Implemented in Categories" = Y)
SpendingCategory = Literal[
    "BEAUTY_PRODUCTS",
    "CAFE_SNACKS",
    "CONFERENCES",
    "DRINKS",
    "EATING_OUT",
    "FOOD_DELIVERY",
    "GIFTS",
    "GROCERIES",
    "GYM",
    "HAIRCUTS",
    "HEALTH_INSURANCE",
    "HOBBIES",
    "HYGIENE",
    "MEDICAL",
    "MOBILE_PLANS",
    "ONLINE_COURSES",
    "OTHER",
    "PERSONAL_TRAINING",
    "RENT",
    "RENT_UTILITIES",
    "SHOPPING_CLOTHES",
    "SHOPPING_OTHER",
    "SOFTWARE_MONTHLY",
    "SOFTWARE_YEARLY",
    "STREAMING_SERVICES",
    "SUPPLEMENTS",
    "TAXI",
    "TBD",
    "TICKETS_TO_EVENTS",
    "TRANSPORT_CITY",
    "TRANSPORT_INTERCITY",
    "TRAVEL_HOUSING",
    "TRAVEL_OTHER",
    "TRAVEL_TRANSPORT",
]

FOOD_CATEGORIES: frozenset[str] = frozenset(
    {
        "EATING_OUT",
        "FOOD_DELIVERY",
        "CAFE_SNACKS",
    }
)


class CategoryData(TypedDict):
    spending_category: SpendingCategory
    note: NotRequired[str]


# Design of category rule functions:
# Input: standardized transaction object with eur_amount field
# Output: Category data dictionary if rule definition matches transaction. None if it doesn't match
type CategoryRuleFunction = Callable[[ImportableTransaction], CategoryData | None]

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

STREAMING_MERCHANTS = ("disney", "netflix", "spotify", "youtube")
STREAMING_PATTERNS = tuple(
    re.compile(f"^.*{pattern}.*$", re.IGNORECASE) for pattern in STREAMING_MERCHANTS
)
FOOD_DELIVERY_MERCHANTS = {"bolt food", "wolt"}
RESTAURANT_MERCHANTS = {
    "A. Taraškienės firma 3515",
    "aloha",
    "Asaki",
    "Beigelistai",
    "berneliu uzeiga",
    "bernelių užeiga",
    "Burna House",
    "Desertas Islandijos G3",
    "Flying Tomato Pizza",
    "Globaltips",
    "Greet.menu",
    "Grill London",
    "Holy Donut",
    "Houdini",
    "ilunch",
    "JAMMI",
    "Jūsų Šnekutis",
    "Ministerija Dienos pietūs",
    "No Forks Mexican Grill",
    "Senolių kepyklėlė",
    "Senolių tradicija",
    "Spirgis",
    "Wokbusters",
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
def eating_out(transaction: ImportableTransaction) -> CategoryData | None:
    counterparty = transaction.counterparty.lower().strip()
    if any(merchant.lower() in counterparty for merchant in RESTAURANT_MERCHANTS):
        return {"spending_category": "EATING_OUT"}

    # Breakfast pattern
    if (
        counterparty in COFFESHOP_MERCHANTS
        and transaction.transaction_datetime.hour < 11
        and transaction.eur_amount > 5
    ):
        return {"spending_category": "EATING_OUT"}

    return None


def food_delivery(transaction: ImportableTransaction) -> CategoryData | None:
    counterparty = transaction.counterparty.lower().strip()
    if any(counterparty == merchant.lower() for merchant in FOOD_DELIVERY_MERCHANTS):
        return {"spending_category": "FOOD_DELIVERY"}
    return None


def streaming_services(transaction: ImportableTransaction) -> CategoryData | None:
    counterparty = transaction.counterparty.lower().strip()
    if any(pattern.search(counterparty) is not None for pattern in STREAMING_PATTERNS):
        return {"spending_category": "STREAMING_SERVICES"}
    return None


def groceries(transaction: ImportableTransaction) -> CategoryData | None:
    counterparty = transaction.counterparty.lower().strip()
    if any(counterparty == merchant.lower() for merchant in SUPERMARKET_MERCHANTS):
        return {"spending_category": "GROCERIES"}
    return None


def hot_drinks(transaction: ImportableTransaction) -> CategoryData | None:
    counterparty = transaction.counterparty.lower().strip()
    if (
        any(counterparty == merchant.lower() for merchant in COFFESHOP_MERCHANTS)
        and transaction.eur_amount <= 5
    ):
        return {"spending_category": "CAFE_SNACKS"}
    return None


def landlord_payment(transaction: ImportableTransaction) -> CategoryData | None:
    to_landlord = transaction.counterparty.upper() == "AUŠRA ADELĖ VAIŠVILĖ"
    if not to_landlord:
        return None

    if transaction.eur_amount >= 400:
        return {"spending_category": "RENT"}

    return {"spending_category": "RENT_UTILITIES"}


def shopping_clothes(transaction: ImportableTransaction) -> CategoryData | None:
    if any(
        pattern.search(transaction.counterparty) is not None
        for pattern in CLOTHES_SHOPPING_PATTERNS
    ):
        return {"spending_category": "SHOPPING_CLOTHES"}

    return None


def shopping_other(transaction: ImportableTransaction) -> CategoryData | None:
    if any(
        pattern.search(transaction.counterparty) is not None
        for pattern in ECOM_MERCHANT_PATTERNS
    ):
        return {"spending_category": "SHOPPING_OTHER"}

    return None


def gym_membership(transaction: ImportableTransaction) -> CategoryData | None:
    if any(
        pattern.search(transaction.counterparty) is not None
        for pattern in GYM_MEMBERSHIP_PATTERNS
    ):
        return {"spending_category": "GYM"}

    return None


# For now, the list of specific categorization rules is setup manually
CATEGORY_RULES: list[CategoryRuleFunction] = [
    streaming_services,
    groceries,
    hot_drinks,
    eating_out,
    food_delivery,
    landlord_payment,
    shopping_clothes,
    shopping_other,
    gym_membership,
]


def get_category_rules() -> list[CategoryRuleFunction]:
    return list(CATEGORY_RULES)
