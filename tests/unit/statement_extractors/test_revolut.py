import datetime as dt
from decimal import Decimal
from io import BytesIO

import openpyxl
import pytest

from app.core.project_types import Side, TransactionSource, TransactionType
from app.statement_extractors.errors import StatementExtractorError
from app.statement_extractors.revolut import (
    RawTransactionRevolut,
    calculate_dedup_key,
    extract_transactions,
    get_note,
    get_side,
    get_transaction_type,
)

EXCEL_HEADERS = (
    "Type",
    "Product",
    "Started Date",
    "Completed Date",
    "Description",
    "Amount",
    "Fee",
    "Currency",
    "State",
    "Balance",
)


def txn_row(overrides: dict | None = None) -> dict:
    row = {
        "Type": "Card Payment",
        "Product": "Current",
        "Started Date": "2026-01-15 10:30:00",
        "Completed Date": "2026-01-17 11:30:00",
        "Description": "Caffeine",
        "Amount": "-5.99",
        "Fee": "0",
        "Currency": "EUR",
        "State": "COMPLETED",
        "Balance": "100.01",
    }
    row.update(overrides or {})
    return row


def build_statement(rows: list[dict]) -> BytesIO:
    """Write xlsx statement data in a BytesIO stream (list of dicts with EXCEL_HEADERS keys), return the written data"""
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.append(list(EXCEL_HEADERS))
    for row in rows:
        sheet.append([row.get(header) for header in EXCEL_HEADERS])
    file_data = BytesIO()
    workbook.save(file_data)

    file_data.seek(0)
    return file_data


def to_raw_txn(row: dict) -> RawTransactionRevolut:
    return RawTransactionRevolut.model_validate(row)


class TestTransactionCustomValidation:
    """Custom validators and normalization in RawTransactionRevolut; filtering rules (Product, State, Type)."""

    def test_validation_model_standardizes_amounts(self):
        """RawTransactionRevolut standardizes amount and balance_after fields to 2 decimals."""
        row = txn_row({"Amount": "10.999", "Balance": "100.1234"})
        raw = RawTransactionRevolut.model_validate(row)
        assert raw.amount == Decimal("11.00")
        assert raw.balance_after == Decimal("100.12")

    def test_only_current_account_transactions_extracted(self):
        """Only Product=Current is valid; other products are rejected."""
        rows = [txn_row(), txn_row({"Product": "Savings"})]
        statement = build_statement(rows)
        result = extract_transactions(statement)
        assert len(result) == 1
        assert result[0].counterparty == "Caffeine"

    @pytest.mark.parametrize("invalid_state", ["PENDING", "REVERTED"])
    def test_only_completed_transactions_extracted(self, invalid_state):
        """Only State=COMPLETED is valid; PENDING and REVERTED are rejected."""
        rows = [txn_row(), txn_row({"State": invalid_state})]
        statement = build_statement(rows)
        result = extract_transactions(statement)
        assert len(result) == 1
        assert result[0].counterparty == "Caffeine"

    @pytest.mark.parametrize(
        "invalid_type",
        [
            "CASHBACK",
            "cashback",
            "Cashback",
            "Exchange",
            "TOPUP",
            "Fee",
            "TRADE",
        ],
    )
    def test_invalid_transaction_types_rejected(self, invalid_type):
        """Unsupported types (CASHBACK, EXCHANGE, TOPUP, FEE, TRADE) are rejected (case-insensitive matching)."""
        statement = build_statement([txn_row({"Type": invalid_type})])
        result = extract_transactions(statement)
        assert len(result) == 0


class TestExtractTransactions:
    """Overall transaction extraction: processing input rows, excluding rejected transactions, input edge cases."""

    def test_returns_expected_data_model(
        self,
    ):
        """Contract: one valid row -> ExtractedTransaction with all fields populated as expected."""
        statement = build_statement([txn_row()])
        result = extract_transactions(statement)
        assert len(result) == 1
        t = result[0]

        assert t.transaction_datetime == dt.datetime(2026, 1, 15, 10, 30, 0)
        assert t.type == TransactionType.CARD_PAYMENT
        assert t.counterparty == "Caffeine"
        assert t.orig_amount == Decimal("5.99")
        assert t.orig_currency == "EUR"
        assert t.side == Side.DEBIT
        assert t.source == TransactionSource.REVOLUT
        assert (
            t.dedup_key
            == "9f3941334e9a03094af0d301ce8de765282f91858d98b064e7c2b7cd6a50f4bc"
        )
        assert t.note is None

    def test_only_valid_transactions_extracted(self):
        """Verifying extracted counts: 22 valid + 6 invalid transactions -> 22 extracted."""
        valid = [txn_row() for _ in range(22)]
        # Invalid product is one of the row rejection reasons - see custom validation tests
        invalid = [txn_row({"Product": "Savings"}) for _ in range(6)]
        statement = build_statement(valid + invalid)
        result = extract_transactions(statement)
        assert len(result) == 22

    def test_empty_statement_returns_empty_list(self):
        """Edge case: no data rows -> 0 extracted."""
        statement = build_statement([])
        result = extract_transactions(statement)
        assert len(result) == 0

    def test_one_transaction_extracted(self):
        """Edge case: single valid row -> 1 extracted."""
        statement = build_statement([txn_row()])
        result = extract_transactions(statement)
        assert len(result) == 1

    def test_multiple_rows_none_valid_returns_empty_list(self):
        """Edge case: all rows invalid (e.g. wrong Product) -> 0 extracted."""
        rows = [txn_row({"Product": "Trading"}) for _ in range(3)]
        statement = build_statement(rows)
        result = extract_transactions(statement)
        assert len(result) == 0


class TestGetTransactionType:
    """Tests for get_transaction_type(transaction) -> TransactionType."""

    @pytest.mark.parametrize(
        ("raw_type", "expected"),
        [
            ("ATM", TransactionType.CASH_WITHDRAWAL),
            ("Card Payment", TransactionType.CARD_PAYMENT),
            ("transfer", TransactionType.TRANSFER),
            ("CARD REFUND", TransactionType.CARD_REFUND),
        ],
    )
    def test_maps_known_input_to_expected_value(self, raw_type, expected):
        raw = to_raw_txn(txn_row({"Type": raw_type}))
        assert get_transaction_type(raw) == expected

    def test_returns_other_for_unknown_input(self):
        """A type that passes validation but is not in the mapping -> OTHER."""
        raw = to_raw_txn(txn_row({"Type": "Subscription"}))
        assert get_transaction_type(raw) == TransactionType.OTHER


class TestGetNote:
    def test_returns_note_for_card_refunds(self):
        raw = to_raw_txn(txn_row({"Type": "Card Refund", "Description": "Amazon"}))
        assert get_note(raw) == "Refund from Amazon"

    def test_returns_none_for_anything_else(self):
        raw = to_raw_txn(txn_row({"Type": "Card Payment"}))
        assert get_note(raw) is None


class TestGetSide:
    @pytest.mark.parametrize(
        ("amount", "expected_side"),
        [
            ("-10.00", Side.DEBIT),
            ("0", Side.DEBIT),
            ("0.01", Side.CREDIT),
            ("100.55", Side.CREDIT),
        ],
    )
    def test_amount_sign_determines_side(self, amount, expected_side):
        raw = to_raw_txn(txn_row({"Amount": amount}))
        assert get_side(raw) == expected_side


class TestCalculateDedupKey:
    def test_same_key_data_produces_same_dedup_key(self):
        row = txn_row()
        raw1 = to_raw_txn(row)
        raw2 = to_raw_txn(row)
        assert calculate_dedup_key(raw1) == calculate_dedup_key(raw2)

    def test_different_started_at_produces_different_key(self):
        raw1 = to_raw_txn(txn_row({"Started Date": "2026-01-15 10:30:00"}))
        raw2 = to_raw_txn(txn_row({"Started Date": "2026-01-15 10:31:00"}))
        assert calculate_dedup_key(raw1) != calculate_dedup_key(raw2)

    def test_different_completed_at_produces_different_key(self):
        raw1 = to_raw_txn(txn_row({"Completed Date": "2026-01-17 11:30:00"}))
        raw2 = to_raw_txn(txn_row({"Completed Date": "2026-01-17 11:31:00"}))
        assert calculate_dedup_key(raw1) != calculate_dedup_key(raw2)

    def test_different_description_produces_different_key(self):
        raw1 = to_raw_txn(txn_row({"Description": "Caffeine"}))
        raw2 = to_raw_txn(txn_row({"Description": "Tea"}))
        assert calculate_dedup_key(raw1) != calculate_dedup_key(raw2)

    def test_different_amount_produces_different_key(self):
        raw1 = to_raw_txn(txn_row({"Amount": "10.00"}))
        raw2 = to_raw_txn(txn_row({"Amount": "20.00"}))
        assert calculate_dedup_key(raw1) != calculate_dedup_key(raw2)

    def test_different_balance_after_produces_different_key(self):
        raw1 = to_raw_txn(txn_row({"Balance": "100.00"}))
        raw2 = to_raw_txn(txn_row({"Balance": "200.00"}))
        assert calculate_dedup_key(raw1) != calculate_dedup_key(raw2)

    def test_normalizes_description_string(self):
        """Description input string is stripped and lowercased before using it in the key."""
        raw1 = to_raw_txn(txn_row({"Description": "Caffeine"}))
        raw2 = to_raw_txn(txn_row({"Description": "  cAffeine  "}))
        assert calculate_dedup_key(raw1) == calculate_dedup_key(raw2)


class TestExceptionMapping:
    def test_raises_standard_exception(self):
        """Statement data can't be read -> StatementExtractorError."""
        statement = BytesIO(b"not an xlsx file")
        with pytest.raises(StatementExtractorError):
            extract_transactions(statement)
