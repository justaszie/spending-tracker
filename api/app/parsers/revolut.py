from hashlib import sha256
from typing import Any, BinaryIO

import openpyxl

from app.project_types import ParsedTransaction, TransactionType, TxnSource, Side


ATTRIBUTES_TO_FILE_HEADERS = {
    "transaction_datetime": "Started Date",
    "counterparty": "Description",
    "orig_amount": "Amount",
    "orig_currency": "Currency",
    "transaction_completed_datetime": "Completed Date",
    "balance_after": "Balance",
    "statement_txn_type": "Type",
}

VALUES_TO_INCLUDE = {
    "Product": {"CURRENT"},
    "State": {"COMPLETED"},
}
VALUES_TO_EXCLUDE = {
    "Type": {"CASHBACK", "EXCHANGE", "TOPUP", "FEE", "TRADE"},
}

TRANSACTION_SOURCE = TxnSource.REVOLUT


def get_raw_transactions(statement: BinaryIO) -> list[dict[str, Any]]:
    # read_only mode auto-closes the excel file
    workbook = openpyxl.load_workbook(statement, read_only=True)
    try:
        sheet = workbook.active
        if not sheet:
            return []

        rows = sheet.iter_rows(values_only=True)
        headers = next(rows)

        raw_txns = [
            {header: value for header, value in zip(headers, row)} for row in rows
        ]

        return raw_txns
    finally:
        workbook.close()


def filter_raw_transactions(transactions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [txn for txn in transactions if is_relevant_transaction(txn)]


def is_relevant_transaction(transaction: dict[str, Any]) -> bool:
    for column, values in VALUES_TO_INCLUDE.items():
        if transaction[column].upper() not in values:
            return False

    for column, values in VALUES_TO_EXCLUDE.items():
        if transaction[column].upper() in values:
            return False

    return True


def clean_raw_transactions(raw_txns: list[dict[str, Any]]) -> list[ParsedTransaction]:
    transactions = []
    for raw_txn in raw_txns:
        transformed = clean_raw_transaction(raw_txn)
        transformed["dedup_key"] = calculate_dedup_key(transformed)
        transformed["type"] = define_transaction_type(transformed)

        transactions.append(ParsedTransaction.model_validate(transformed))

    return transactions


def clean_raw_transaction(raw_transaction: dict[str, Any]) -> dict[str, Any]:
    clean_transaction = {
        attribute: raw_transaction.get(header)
        for attribute, header in ATTRIBUTES_TO_FILE_HEADERS.items()
    }

    clean_transaction["side"] = (
        Side.DEBIT if clean_transaction["orig_amount"] <= 0 else Side.CREDIT
    )

    clean_transaction["orig_amount"] = abs(clean_transaction["orig_amount"])

    if raw_transaction["Type"].upper() == "CARD REFUND":
        clean_transaction["note"] = f"Refund from {clean_transaction['counterparty']}"

    clean_transaction["source"] = TRANSACTION_SOURCE

    return clean_transaction


def parse_revolut_statement(statement: BinaryIO) -> list[ParsedTransaction]:
    raw_txns = get_raw_transactions(statement)
    filtered = [txn for txn in raw_txns if is_relevant_transaction(txn)]
    clean_txns = clean_raw_transactions(filtered)

    return clean_txns


def calculate_dedup_key(transaction: dict[str, Any]) -> str:
    dedup_data = (
        f"{str(transaction['transaction_datetime']).strip().lower()}_"
        f"{str(transaction['transaction_completed_datetime']).strip().lower()}_"
        f"{str(transaction['counterparty']).strip().lower()}_"
        f"{str(transaction['orig_amount']).strip().lower()}_"
        f"{str(transaction['balance_after']).strip().lower()}_"
    )

    hash_algo = sha256()
    hash_algo.update(dedup_data.encode())

    return hash_algo.hexdigest()


def define_transaction_type(transaction: dict[str, Any]) -> TransactionType:
    match transaction.get("statement_txn_type"):
        case "ATM":
            return TransactionType.CASH_WITHDRAWAL
        case "Card Payment":
            return TransactionType.CARD_PAYMENT
        case "Transfer":
            return TransactionType.TRANSFER
        case _:
            return TransactionType.OTHER
