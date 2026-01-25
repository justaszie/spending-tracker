import re
from csv import DictReader
from io import TextIOWrapper
from hashlib import sha256
from typing import Any, BinaryIO

from app.project_types import ParsedTransaction, TxnSource, Side


ATTRIBUTES_TO_FILE_HEADERS = {
    "transaction_datetime": "Data",
    "counterparty": "Gavėjas",
    "orig_amount": "Suma",
    "orig_currency": "Valiuta",
    "note": "Paaiškinimai",
    "unique_id": "Įrašo Nr.",
}

EXCL_TRANSCTION_DESCRIPTION_PATTERNS = (
    r"^apyvarta$",
    r"^likutis .*$",
    r"paslaugų plano(.+ mokestis.*)?$",
)

TRANSACTION_SOURCE = TxnSource.SWEDBANK


def get_raw_transactions(statement: BinaryIO) -> list[dict[str, Any]]:
    # Input: csv file data
    # Output: list of dictionaries (mapping column to value for each row in csv)
    text_reader = TextIOWrapper(statement)
    dict_reader = DictReader(text_reader)
    return [txn_as_dict for txn_as_dict in dict_reader]


def filter_raw_transactions(transactions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [txn for txn in transactions if is_relevant_transaction(txn)]


def is_relevant_transaction(transaction: dict[str, Any]) -> bool:
    counterparty = transaction["Gavėjas"].upper()
    note = transaction["Paaiškinimai"].upper()

    # Exclude transfers to / from my own other accounts
    if counterparty == "JUSTAS ZIEMINYKAS":
        return False

    # Exclude cash withdrawals
    if note is not None and "GRYNIEJI" in note.upper():
        return False

    # Exclude entries such as total amount spent during period.
    # The format for such transactions is that there's no counterparty
    # and the note field matches specific patterns like "apyvarta..."
    if not counterparty and any(
        [
            re.search(pattern, note, re.IGNORECASE) is not None
            for pattern in EXCL_TRANSCTION_DESCRIPTION_PATTERNS
        ]
    ):
        return False

    return True


def clean_raw_transactions(raw_txns: list[dict[str, Any]]) -> list[ParsedTransaction]:
    transactions = []
    for raw_txn in raw_txns:
        transformed = clean_raw_transaction(raw_txn)

        dedup_key = calculate_dedup_key(transformed)
        transformed["dedup_key"] = dedup_key

        transactions.append(ParsedTransaction.model_validate(transformed))

    return transactions


def clean_raw_transaction(raw_transaction: dict[str, Any]) -> dict[str, Any]:
    # Collects the relevant attributes to a dict
    clean_transaction = {
        attribute: raw_transaction.get(header)
        for attribute, header in ATTRIBUTES_TO_FILE_HEADERS.items()
    }

    # If no counterparty in the original field, we use note field that should have some info
    if clean_transaction["counterparty"] == "":
        clean_transaction["counterparty"] = clean_transaction.get("note")

    clean_transaction["source"] = TRANSACTION_SOURCE

    clean_transaction["side"] = Side.DEBIT if raw_transaction["D/K"] == "D" else Side.CREDIT

    return clean_transaction


def parse_swedbank_statement(statement: BinaryIO) -> list[ParsedTransaction]:
    raw_txns = get_raw_transactions(statement)
    filtered = [txn for txn in raw_txns if is_relevant_transaction(txn)]
    clean_txns = clean_raw_transactions(filtered)

    return clean_txns


def calculate_dedup_key(transaction: dict[str, Any]) -> str:
    dedup_data = str(transaction["unique_id"]).strip().lower()

    hash_algo = sha256()
    hash_algo.update(dedup_data.encode())

    return hash_algo.hexdigest()
