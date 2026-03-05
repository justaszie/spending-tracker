import csv
import datetime as dt
from decimal import Decimal
from io import BytesIO, StringIO

import pytest

from app.core.project_types import Side, TransactionSource, TransactionType
from app.statement_extractors.errors import StatementExtractorError
from app.statement_extractors.swedbank import (
    RawTransactionSwedbank,
    calculate_dedup_key,
    extract_transactions,
    get_counterparty,
    get_side,
    get_transaction_type,
)

CSV_HEADERS = (
    "Sąskaitos Nr.",
    # File contains columns with no names - we name it to be able to create test data
    "_unnamed_col_1",
    "Data",
    "Gavėjas",
    "Paaiškinimai",
    "Suma",
    "Valiuta",
    "D/K",
    "Įrašo Nr.",
    "Kodas",
    "Įmokos kodas",
    "Dok. Nr.",
    "Kliento kodas mokėtojo IS",
    "Kliento kodas",
    "Pradinis mokėtojas",
    "Galutinis gavėjas",
)


def txn_row(overrides: dict | None = None) -> dict:
    row = {
        "Sąskaitos Nr.": "LT647300010112345678",
        "_unnamed_col_1": "20",
        "Data": "2026-01-11",
        "Gavėjas": "DeezerEUROPE DEEZER 75009 Paris",
        "Paaiškinimai": "PIRKINYS 516793******2437 2025.08.28 71.94 EUR (583569) DeezerEUROPE DEEZER 75009 Paris",
        "Suma": "71.94",
        "Valiuta": "EUR",
        "D/K": "D",
        "Įrašo Nr.": "2025083000256789",
        "Kodas": "K",
        "Įmokos kodas": "101",
        "Dok. Nr.": "90",
        "Kliento kodas mokėtojo IS": "",
        "Kliento kodas": "",
        "Pradinis mokėtojas": "",
        "Galutinis gavėjas": "",
    }
    row.update(overrides or {})
    return row


def build_statement(rows: list[dict]) -> BytesIO:
    """Write CSV statement data into a BytesIO stream, return the written data."""
    stream = StringIO()
    writer = csv.writer(stream)
    writer.writerow(CSV_HEADERS)
    for row in rows:
        writer.writerow([row.get(header) for header in CSV_HEADERS])

    file_data = BytesIO(stream.getvalue().encode("utf-8"))
    file_data.seek(0)
    return file_data


def to_raw_txn(row: dict) -> RawTransactionSwedbank:
    return RawTransactionSwedbank.model_validate(row)


class TestTransactionCustomValidation:
    """Custom validators and normalization in RawTransactionSwedbank."""

    @pytest.mark.parametrize("invalid_side", ["C", "DK", ""])
    def test_rejects_invalid_debit_credit_values(self, invalid_side):
        """Side field: any other value than 'D' or 'K' -> row rejected."""
        statement = build_statement([txn_row({"D/K": invalid_side})])
        result = extract_transactions(statement)
        assert len(result) == 0

    @pytest.mark.parametrize(
        "description",
        ["apyvarta", "APYVARTA", "likutis 2026.01.01", "Likutis something"],
    )
    def test_rejects_invalid_description_patterns(self, description):
        """Descriptions matching EXCL_DESCRIPTION_PATTERNS are rejected."""
        statement = build_statement([txn_row({"Paaiškinimai": description})])
        result = extract_transactions(statement)
        assert len(result) == 0

    def test_validation_model_standardizes_amounts(self):
        """Amount is standardized (e.g. to 2 decimals) by the raw model."""
        row = txn_row({"Suma": "10.1555"})
        raw = RawTransactionSwedbank.model_validate(row)
        assert raw.amount == Decimal("10.16")


class TestExtractTransactions:
    """Overall transaction extraction: processing input rows, excluding rejected transactions, input edge cases."""

    def test_returns_expected_data_model(self):
        """Contract: one valid row -> ExtractedTransaction with all fields populated as expected."""
        statement = build_statement([txn_row()])
        result = extract_transactions(statement)
        assert len(result) == 1
        t = result[0]

        assert isinstance(t.dedup_key, str)
        assert t.note is None or isinstance(t.note, str)
        assert t.transaction_datetime == dt.datetime(2026, 1, 11, 0, 0, 0)
        assert t.type == TransactionType.CARD_PAYMENT
        assert t.counterparty == "DeezerEUROPE DEEZER 75009 Paris"
        assert t.orig_amount == Decimal("71.94")
        assert t.orig_currency == "EUR"
        assert t.side == Side.DEBIT
        assert t.source == TransactionSource.SWEDBANK
        assert (
            t.dedup_key
            == "d4685410dd4a3d20713e63fe980e3d48518f79ef286a989986a67bab2d16626a"
        )

    def test_only_valid_transactions_extracted(self):
        """Verifying extracted counts: 22 valid + 6 invalid transactions -> 22 extracted."""
        valid = [txn_row() for _ in range(22)]
        invalid = [txn_row({"D/K": "X"}) for _ in range(6)]
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
        """All rows invalid (e.g. wrong D/K) -> 0 extracted."""
        rows = [txn_row({"D/K": "X"}) for _ in range(3)]
        statement = build_statement(rows)
        result = extract_transactions(statement)
        assert len(result) == 0


class TestCalculateDedupKey:
    """Dedup key is based on unique_id (Įrašo Nr.)."""

    def test_same_unique_id_produces_same_dedup_key(self):
        row = txn_row({"Įrašo Nr.": "2025083000256789"})
        raw1 = to_raw_txn(row)
        raw2 = to_raw_txn(row)
        assert calculate_dedup_key(raw1) == calculate_dedup_key(raw2)

    def test_different_unique_id_produces_different_dedup_key(self):
        raw1 = to_raw_txn(txn_row({"Įrašo Nr.": "2025083000256789"}))
        raw2 = to_raw_txn(txn_row({"Įrašo Nr.": "2025083000256790"}))
        assert calculate_dedup_key(raw1) != calculate_dedup_key(raw2)

    def test_normalizes_input_string(self):
        raw1 = to_raw_txn(txn_row({"Įrašo Nr.": "2025083000256789"}))
        raw2 = to_raw_txn(txn_row({"Įrašo Nr.": "  2025083000256789 "}))
        assert calculate_dedup_key(raw1) == calculate_dedup_key(raw2)


class TestGetCounterparty:
    """Counterparty: use "Gavėjas" when populated, otherwise use description."""

    def test_uses_original_counterparty(self):
        raw = to_raw_txn(txn_row({"Gavėjas": "Some Merchant"}))
        assert get_counterparty(raw) == "Some Merchant"

    def test_uses_description_when_no_counterparty(self):
        raw = to_raw_txn(
            txn_row({"Gavėjas": "", "Paaiškinimai": "Fallback description"})
        )
        assert get_counterparty(raw) == "Fallback description"


class TestGetTransactionType:
    """Transaction type from Kodas and description."""

    def test_detects_cash_withdrawals(self):
        raw = to_raw_txn(txn_row({"Kodas": "K", "Paaiškinimai": "grynieji ATM 123"}))
        assert get_transaction_type(raw) == TransactionType.CASH_WITHDRAWAL

    def test_detects_card_payments(self):
        raw = to_raw_txn(txn_row({"Kodas": "K"}))
        assert get_transaction_type(raw) == TransactionType.CARD_PAYMENT

    def test_detects_transfers(self):
        raw = to_raw_txn(txn_row({"Kodas": "MK"}))
        assert get_transaction_type(raw) == TransactionType.TRANSFER

    def test_returns_other_for_unknown_input(self):
        raw = to_raw_txn(txn_row({"Kodas": "X"}))
        assert get_transaction_type(raw) == TransactionType.OTHER


class TestGetSide:
    """Side: D -> DEBIT, any other valid value -> CREDIT."""

    def test_returns_debit_for_d_side(self):
        raw = to_raw_txn(txn_row({"D/K": "D"}))
        assert get_side(raw) == Side.DEBIT

    def test_returns_debit_for_k_side(self):
        raw = to_raw_txn(txn_row({"D/K": "K"}))
        assert get_side(raw) == Side.CREDIT


class TestExceptionMapping:
    """Statement unreadable -> StatementExtractorError."""

    def test_raises_standard_exception(self):
        statement = BytesIO(b"")
        # Trying to read from closed stream will raise an exception
        statement.close()
        with pytest.raises(StatementExtractorError):
            extract_transactions(statement)
