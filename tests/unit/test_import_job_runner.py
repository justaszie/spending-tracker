from decimal import Decimal
from io import BytesIO
import uuid

import pytest

from app.core.project_types import (
    ImportJobStatus,
    Side,
    StatementSource,
)
from app.db.statement_import_jobs import StatementImportJob, create_new_job, load_job
from app.db.transactions import Transaction, insert_transactions
from app.import_job_runner import (
    BusinessRuleFilterError,
    CurrencyConversionError,
    ExistingTransactionSeparationError,
    ExtractorNotFoundError,
    JobNotFoundError,
    StatementDownloadError,
    StatementExtractorError,
    TransactionInsertError,
    add_eur_amount,
    apply_business_filter,
    enrich_transactions,
    get_extracted_transactions,
    import_transactions,
    record_job_failure,
    run_job,
    separate_new_existing,
    update_job_completed,
    update_job_failed,
    update_job_start,
)


## HELPERS
def sample_job(**overrides):
    data = {
        "statement_source": StatementSource.REVOLUT,
        "file_path": "./some/path",
    }
    data.update(overrides)
    return StatementImportJob(**data)


def insert_sample_job(test_db):
    job = sample_job()
    return create_new_job(new_job=job, db=test_db)


class TestJobStatusUpdates:
    def test_updates_failed(self, test_db):
        existing_job = insert_sample_job(test_db)

        updated_job = update_job_failed(
            job=existing_job, failure_reason="EXTRACTOR_NOT_FOUND", db=test_db
        )

        stored_job = load_job(job_id=updated_job.id, db=test_db)
        assert stored_job.id == existing_job.id
        assert stored_job.updated_at is not None
        assert stored_job.failure_reason == "EXTRACTOR_NOT_FOUND"
        assert stored_job.status == ImportJobStatus.FAILED

    def test_updates_start(self, test_db):
        existing_job = insert_sample_job(test_db)

        updated_job = update_job_start(job=existing_job, db=test_db)

        stored_job = load_job(job_id=updated_job.id, db=test_db)
        assert stored_job.id == existing_job.id
        assert stored_job.started_at is not None
        assert stored_job.updated_at == stored_job.started_at
        assert stored_job.status == ImportJobStatus.RUNNING

    def test_updates_completed(self, test_db):
        existing_job = insert_sample_job(test_db)

        updated_job = update_job_completed(
            job=existing_job,
            imported_txn_count=5,
            duplicate_txn_count=2,
            db=test_db,
        )

        stored_job = load_job(job_id=updated_job.id, db=test_db)
        assert stored_job.id == existing_job.id
        assert stored_job.completed_at is not None
        assert stored_job.updated_at == stored_job.completed_at
        assert stored_job.status == ImportJobStatus.COMPLETED
        assert stored_job.imported_txn_count == 5
        assert stored_job.duplicate_txn_count == 2


class TestRecordJobFailure:
    @pytest.mark.parametrize(
        ("exc", "expected_reason"),
        [
            (CurrencyConversionError(), "CURRENCY_CONVERSION_ERROR"),
            (StatementDownloadError(), "STATEMENT_LOAD_ERROR"),
            (ExtractorNotFoundError(), "EXTRACTOR_NOT_FOUND"),
            (StatementExtractorError(), "TRANSACTIONS_EXTRACTION_ERROR"),
            (BusinessRuleFilterError(), "BUSINESS_RULE_FILTER_ERROR"),
            (ExistingTransactionSeparationError(), "NEW_EXISTING_SEPARATION_ERROR"),
            (TransactionInsertError(), "TRANSACTION_INSERT_ERROR"),
        ],
    )
    def test_known_exception_updates_job_with_expected_failure_reason(
        self, test_db, exc, expected_reason
    ):
        existing_job = insert_sample_job(test_db)

        record_job_failure(job=existing_job, e=exc, db=test_db)

        stored_job = load_job(job_id=existing_job.id, db=test_db)
        assert stored_job.id == existing_job.id
        assert stored_job.status == ImportJobStatus.FAILED
        assert stored_job.updated_at is not None
        assert stored_job.failure_reason == expected_reason

    def test_unknown_exception_updates_job_with_other_error(self, test_db):
        existing_job = insert_sample_job(test_db)

        record_job_failure(job=existing_job, e=ValueError("unexpected"), db=test_db)

        stored_job = load_job(job_id=existing_job.id, db=test_db)
        assert stored_job.id == existing_job.id
        assert stored_job.status == ImportJobStatus.FAILED
        assert stored_job.updated_at is not None
        assert stored_job.failure_reason == "OTHER_ERROR"


class TestRunJob:
    def test_raises_custom_exc_when_job_not_found(self, test_db, mocker):
        """When the job doesn't exist, the job runner must propagate a custom error."""

        nonexisting_job_id = uuid.uuid4()
        with pytest.raises(JobNotFoundError):
            run_job(
                job_id=nonexisting_job_id,
                user_id=uuid.uuid4(),
                db=test_db,
                file_storage=mocker.Mock(),
                statements_bucket="statements",
            )


class TestGetExtractedTransactions:
    def test_raises_custom_exc_when_extractor_not_found(self, mocker):
        """When no extractor is registered for the source, raises ExtractorNotFoundError."""
        mocker.patch("app.import_job_runner.get_extractor_fn", return_value=None)

        with pytest.raises(ExtractorNotFoundError):
            get_extracted_transactions(
                statement_data=BytesIO(b"statement bytes"),
                statement_source=StatementSource.REVOLUT,
            )


class TestApplyBusinessFilter:
    def test_raises_custom_exc_when_something_fails(self, mocker):
        """When something in the function raises, the function raises BusinessRuleFilterError."""
        mocker.patch(
            "app.import_job_runner.get_filter_rules",
            side_effect=ValueError("filter rules error"),
        )

        with pytest.raises(BusinessRuleFilterError):
            apply_business_filter([])

    def test_nothing_filtered(self, extracted_transaction):
        """When the rule passes for all transactions, all are returned."""

        def keep_all(_txn):
            return True

        txn_a = extracted_transaction(dedup_key="key-a")
        txn_b = extracted_transaction(dedup_key="key-b")
        result = apply_business_filter([txn_a, txn_b], filter_rules=[keep_all])
        assert result == [txn_a, txn_b]

    def test_everything_filtered_out(self, extracted_transaction):
        """When the rule fails for all transactions, result is empty."""

        def keep_none(_txn):
            return False

        txn_a = extracted_transaction(dedup_key="key-a")
        txn_b = extracted_transaction(dedup_key="key-b")
        result = apply_business_filter([txn_a, txn_b], filter_rules=[keep_none])
        assert result == []

    def test_some_filtered_out(self, extracted_transaction):
        """When the rule fails for some transactions, only passing ones are returned."""

        def keep_if_not_excluded(txn):
            return txn.counterparty != "EXCLUDE"

        txn_keep = extracted_transaction(dedup_key="key-1", counterparty="BrewDog Pub")
        txn_drop = extracted_transaction(dedup_key="key-2", counterparty="EXCLUDE")
        result = apply_business_filter(
            [txn_keep, txn_drop], filter_rules=[keep_if_not_excluded]
        )
        assert result == [txn_keep]


class TestSeparateNewExisting:
    def test_separates_all_new(self, test_db, extracted_transaction):
        """When no transaction dedup_key is in existing keys, all go to new."""
        user_id = uuid.uuid4()
        txn_a = extracted_transaction(dedup_key="key-a")
        txn_b = extracted_transaction(dedup_key="key-b")
        result = separate_new_existing(
            transactions=[txn_a, txn_b],
            user_id=user_id,
            db=test_db,
        )
        assert result["new"] == [txn_a, txn_b]
        assert result["existing"] == []

    def test_separates_all_existing(
        self, test_db, db_transaction, extracted_transaction
    ):
        """When every transaction dedup_key is in existing keys, all go to existing."""
        user_id = uuid.uuid4()
        insert_transactions(
            [
                db_transaction(user_id=user_id, dedup_key="key-a"),
                db_transaction(user_id=user_id, dedup_key="key-b"),
            ],
            db=test_db,
        )
        txn_a = extracted_transaction(dedup_key="key-a")
        txn_b = extracted_transaction(dedup_key="key-b")
        result = separate_new_existing(
            transactions=[txn_a, txn_b],
            user_id=user_id,
            db=test_db,
        )
        assert result["new"] == []
        assert result["existing"] == [txn_a, txn_b]

    def test_separates_new_from_existing(
        self, test_db, db_transaction, extracted_transaction
    ):
        """When some dedup_keys are in existing keys, they go to existing; rest to new."""
        user_id = uuid.uuid4()
        insert_transactions(
            [
                db_transaction(user_id=user_id, dedup_key="key-existing-1"),
                db_transaction(user_id=user_id, dedup_key="key-existing-2"),
            ],
            db=test_db,
        )
        txn_new = extracted_transaction(dedup_key="key-new")
        txn_existing = extracted_transaction(dedup_key="key-existing-1")
        result = separate_new_existing(
            transactions=[txn_new, txn_existing],
            user_id=user_id,
            db=test_db,
        )
        assert result["new"] == [txn_new]
        assert result["existing"] == [txn_existing]

    def test_considers_new_when_dedup_key_exists_different_user(
        self, test_db, db_transaction, extracted_transaction
    ):
        """Transaction with dedup_key that exists only for another user is considered new."""
        other_user_id = uuid.uuid4()
        current_user_id = uuid.uuid4()
        insert_transactions(
            [db_transaction(user_id=other_user_id, dedup_key="key-shared")],
            db=test_db,
        )
        txn = extracted_transaction(dedup_key="key-shared")
        result = separate_new_existing(
            transactions=[txn],
            user_id=current_user_id,
            db=test_db,
        )
        assert result["new"] == [txn]
        assert result["existing"] == []

    def test_returns_empty_lists_when_empty_input(self, test_db):
        result = separate_new_existing(
            transactions=[], user_id=uuid.uuid4(), db=test_db
        )
        assert result["new"] == []
        assert result["existing"] == []

    def test_raises_custom_exc_when_something_fails(self, test_db, mocker):
        """When something in the function raises, the function raises ExistingTransactionSeparationError."""
        mocker.patch(
            "app.import_job_runner.get_existing_dedup_keys",
            side_effect=Exception("db error"),
        )

        with pytest.raises(ExistingTransactionSeparationError):
            separate_new_existing(
                transactions=[],
                user_id=uuid.uuid4(),
                db=test_db,
            )


class TestAddEurAmount:
    def test_raises_custom_exc_when_something_fails(
        self, mocker, extracted_transaction
    ):
        """When something in the function raises, the function raises."""
        mocker.patch(
            "app.import_job_runner.CurrencyConverter",
            side_effect=Exception("connection failed"),
        )

        with pytest.raises(CurrencyConversionError):
            add_eur_amount([extracted_transaction()])

    def test_adds_eur_amounts_to_transactions(self, mocker, extracted_transaction):
        # TODO - simplify - just a few transactions and they all have eur amounts stubbed
        """Input with EUR and non-EUR transactions; output has correct eur_amount from stub."""
        txn_eur = extracted_transaction(
            dedup_key="eur-1",
            orig_currency="EUR",
            orig_amount=Decimal("10.00"),
        )
        txn_gbp = extracted_transaction(
            dedup_key="gbp-1",
            orig_currency="GBP",
            orig_amount=Decimal("5.00"),
        )

        def stub_get_eur_amount(*, orig_currency, orig_amount, **_unused):
            if orig_currency == "EUR":
                return orig_amount
            if orig_currency == "GBP":
                return Decimal("5.85")
            return orig_amount

        mocker.patch(
            "app.import_job_runner.get_eur_amount",
            side_effect=stub_get_eur_amount,
        )

        result = add_eur_amount(
            [txn_eur, txn_gbp],
            currency_converter=mocker.Mock(),
        )

        assert len(result) == 2
        assert result[0].dedup_key == "eur-1"
        assert result[0].eur_amount == Decimal("10.00")
        assert result[1].dedup_key == "gbp-1"
        assert result[1].eur_amount == Decimal("5.85")


class TestEnrichTransactions:
    def test_gets_categories_for_debit_txns(self, mocker, importable_transaction):
        """Input batch: some get category data, some don't. Output same length, correct values."""
        with_category_1 = importable_transaction(
            dedup_key="a", side=Side.DEBIT, note=None
        )
        with_category_2 = importable_transaction(
            dedup_key="b", side=Side.DEBIT, note=None
        )
        without_category = importable_transaction(dedup_key="c", side=Side.CREDIT)
        batch = [with_category_1, without_category, with_category_2]

        mocker.patch(
            "app.import_job_runner.get_category_data",
            return_value={
                "spending_category": "EATING_OUT",
                "note": "some note about spending",
            },
        )
        mocker.patch(
            "app.import_job_runner.get_meal_type",
            return_value="Lunch",
        )

        result = enrich_transactions(batch)

        assert len(result) == len(batch)
        expected_category = (result[0], result[2])
        for txn in expected_category:
            assert txn.spending_category == "EATING_OUT"
            assert txn.meal_type == "Lunch"

        expected_no_category = result[1]
        assert expected_no_category.spending_category is None
        assert expected_no_category.meal_type is None

    def test_note_updated_only_when_empty(self, mocker, importable_transaction):
        """Note is set from category when empty; existing note is kept otherwise."""
        empty_note = importable_transaction(dedup_key="e", side=Side.DEBIT, note=None)
        has_note = importable_transaction(
            dedup_key="h", side=Side.DEBIT, note="present before categorization"
        )
        batch = [empty_note, has_note]

        mocker.patch(
            "app.import_job_runner.get_category_data",
            return_value={
                "spending_category": "EATING_OUT",
                "note": "note set by categorization",
            },
        )
        mocker.patch("app.import_job_runner.get_meal_type")

        result = enrich_transactions(batch)

        assert result[0].note == "note set by categorization"
        assert result[1].note == "present before categorization"


class TestImportTransactions:
    def test_imports_and_returns_db_transaction_instances(
        self, test_db, importable_transaction
    ):
        """Input small batch; all inserted and return value is list of Transaction instances."""
        job = insert_sample_job(test_db)
        user_id = uuid.uuid4()
        txn_a = importable_transaction(dedup_key="import-key-a")
        txn_b = importable_transaction(dedup_key="import-key-b")
        batch = [txn_a, txn_b]

        result = import_transactions(
            transactions=batch,
            user_id=user_id,
            job_id=job.id,
            db=test_db,
        )

        assert len(result) == len(batch)
        # Verify that the returned objects are DB transaction instances matching the input
        for t in result:
            assert isinstance(t, Transaction)
            assert t.id is not None
            assert t.dedup_key in {"import-key-a", "import-key-b"}

    def test_amounts_quantized_to_2_decimals(self, test_db, importable_transaction):
        """ImportableTransaction enforces 2-decimal quantization; inserted Transaction has quantized amounts."""
        job = insert_sample_job(test_db)
        user_id = uuid.uuid4()
        txn = importable_transaction(
            dedup_key="quant-key",
            orig_amount=Decimal("10.126"),
            eur_amount=Decimal("5.999"),
        )

        result = import_transactions(
            transactions=[txn],
            user_id=user_id,
            job_id=job.id,
            db=test_db,
        )

        assert len(result) == 1
        inserted = result[0]
        # ImportableTransaction enforces 2-decimal quantization; stored amounts are 2 decimals
        assert inserted.orig_amount == Decimal("10.13")
        assert inserted.eur_amount == Decimal("6.00")

    def test_imported_transaction_has_all_required(
        self, test_db, importable_transaction
    ):
        """One inserted Transaction contains all fields from ImportableTransaction (spending_category, meal_type, etc.)."""
        job = insert_sample_job(test_db)
        user_id = uuid.uuid4()
        txn = importable_transaction(
            dedup_key="full-fields-key",
            counterparty="Cafe",
            note="lunch",
            spending_category="EATING_OUT",
            meal_type="Lunch",
        )

        result = import_transactions(
            transactions=[txn],
            user_id=user_id,
            job_id=job.id,
            db=test_db,
        )

        inserted = result[0]
        assert inserted.transaction_datetime == txn.transaction_datetime
        assert inserted.type == txn.type
        assert inserted.counterparty == "Cafe"
        assert inserted.orig_amount == txn.orig_amount
        assert inserted.orig_currency == txn.orig_currency
        assert inserted.side == txn.side
        assert inserted.source == txn.source
        assert inserted.eur_amount == txn.eur_amount
        assert inserted.note == "lunch"
        assert inserted.spending_category == "EATING_OUT"
        assert inserted.meal_type == "Lunch"
        assert inserted.dedup_key == "full-fields-key"
        assert inserted.user_id == user_id
        assert inserted.import_job_id == job.id
        assert inserted.manually_added is False
