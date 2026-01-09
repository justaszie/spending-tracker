from typing import Any, BinaryIO

import openpyxl

from app.project_types import ParsedTransaction, TxnSource


ATTRIBUTES_TO_FILE_HEADERS = {
    "transaction_date": "Started Date",
    "counterparty": "Description",
    "orig_amount": "Amount",
    "orig_currency": "Currency",
}

VALUES_TO_INCLUDE = {
    "Product": {"Current"},
}
VALUES_TO_EXCLUDE = {
    "Type": {"CASHBACK", "EXCHANGE", "TOPUP", "FEE", "TRADE"},
    "State": {"REVERTED"},
    "Description": {
        "TO GBP",
        "TO GBP SAVINGS",
        "TO JUSTAS Å½IEMINYKAS",
        "TO JUSTAS ŽIEMINYKAS",
        "TO USD",
        "TO INVESTMENT ACCOUNT",
    },
}

TRANSACTION_SOURCE = TxnSource.REVOLUT


# TODO: consider typed dict or even BaseModel for raw transactions for more precision
# This way, in the functions I'd access attributes and if format changes, I only change one place: model definition.
def get_raw_transactions(statement: BinaryIO) -> list[dict[str, Any]]:
    # read_only mode auto-closes the excel file
    workbook = openpyxl.load_workbook(statement, read_only=True)
    try:
        sheet = workbook.active
        if not sheet:
            # TODO: Log that couldn't get the sheet
            return []

        rows = sheet.iter_rows(values_only=True)
        headers = next(rows)

        # TODO: Edge cases: empty rows, then non-empy rows after empty ones, etc.
        raw_txns = [
            {header: value for header, value in zip(headers, row)} for row in rows
        ]
        return raw_txns
    finally:
        workbook.close()


def filter_raw_transactions(transactions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [txn for txn in transactions if is_relevant_transaction(txn)]


# TODO: DIP: consider creating Filter abstraction and pass list of filters to this
# so we can just call Filter.apply(txn) or similar
# This would add observability - which rule discarded a particular tranasction
def is_relevant_transaction(transaction: dict[str, Any]) -> bool:
    for column, values in VALUES_TO_INCLUDE.items():
        if transaction[column] not in values:
            return False

    for column, values in VALUES_TO_EXCLUDE.items():
        if transaction[column] in values:
            return False

    return True


def clean_raw_transactions(raw_txns: list[dict[str, Any]]) -> list[ParsedTransaction]:
    transactions = []
    for raw_txn in raw_txns:
        transformed = clean_raw_transaction(raw_txn)
        transactions.append(ParsedTransaction.model_validate(transformed))

    return transactions


def clean_raw_transaction(raw_transaction: dict[str, Any]) -> dict[str, Any]:
    clean_transaction = {
        attribute: raw_transaction[header]
        for attribute, header in ATTRIBUTES_TO_FILE_HEADERS.items()
    }

    clean_transaction["side"] = (
        "Debit" if clean_transaction["orig_amount"] <= 0 else "Credit"
    )

    clean_transaction["orig_amount"] = abs(clean_transaction["orig_amount"])

    # TODO: Avoid magic string value - maybe set up Enum for raw data values
    if raw_transaction["Type"].upper() == "CARD REFUND":
        clean_transaction["note"] = f"Refund from {clean_transaction['counterparty']}"


    clean_transaction["source"] = TRANSACTION_SOURCE

    return clean_transaction


def parse_revolut_statement(statement: BinaryIO) -> list[ParsedTransaction]:
    raw_txns = get_raw_transactions(statement)
    filtered = [txn for txn in raw_txns if is_relevant_transaction(txn)]
    # TODO: Store and log discarded transactions somewhere easy, like csv.
    clean_txns = clean_raw_transactions(filtered)

    return clean_txns
