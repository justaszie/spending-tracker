from collections.abc import Iterable
from pathlib import Path
from typing import TypedDict
from uuid import UUID
import datetime as dt
import logging

from currency_converter import ECB_URL, CurrencyConverter
from sqlalchemy import Engine
import pandas as pd

from app.business_rules.filter_rules import FilterRuleFN, get_filter_rules
from app.core.config import AppEnvironment
from app.core.dependencies import AppConfig
from app.core.project_types import (
    ExtractedTransaction,
    ImportableTransaction,
    ImportJobStatus,
    Side,
)
from app.db.statement_import_jobs import StatementImportJob, load_job, update_job
from app.db.transactions import (
    Transaction,
    TransactionInsertError,
    get_existing_dedup_keys,
    insert_transactions,
)
from app.enrichment import (
    CurrencyConversionError,
    get_category_data,
    get_eur_amount,
    get_meal_type,
)
from app.statement_extractors.errors import StatementExtractorError
from app.statement_extractors.registry import get_extractor_fn
from app.storage.file_storage import FileStorage, StatementDownloadError

logger = logging.getLogger(__name__)


class JobNotFoundError(Exception):
    pass


class ExtractorNotFoundError(Exception):
    pass


class BusinessRuleFilterError(Exception):
    pass


class ExistingTransactionSeparationError(Exception):
    pass


class JobFailureDetails(TypedDict):
    job_failure_reason: str
    error_message: str


class NewExistingSeparation(TypedDict):
    new: list[ExtractedTransaction]
    existing: list[ExtractedTransaction]


def run_job(
    job_id: UUID,
    user_id: UUID,
    db: Engine,
    file_storage: FileStorage,
    app_config: AppConfig,
) -> None:
    # Load job info
    job = load_job(job_id, db)
    if not job:
        # If we get wrong job_id, it's the responsibility of the caller
        raise JobNotFoundError(f"Job not found for id: {job_id}")

    update_job_start(job=job, db=db)
    logger.info(f"Starting Job: {job.id} for {job.statement_source}")

    try:
        # Load the statement from file storage
        statement = file_storage.load_file(
            job.file_path, bucket=app_config.STATEMENTS_STORAGE_BUCKET
        )
        logger.info(f"Downloaded statement from: {job.file_path}")

        # Find the right extractor for the statement
        extractor_fn = get_extractor_fn(job.statement_source)
        if extractor_fn is None:
            raise ExtractorNotFoundError(
                f'Exractor not found for statement source: "{job.statement_source}"'
            )

        # Get extracted transactions in standard format
        extracted: list[ExtractedTransaction] = extractor_fn(statement)

        # Apply filtering rules to exclude irrelevant transactions
        filtered = apply_business_filter(extracted)
        logger.info(
            f"Completed business rules filtering. Before filtering: {len(extracted)} | After filtering: {len(filtered)}"
        )

        separated = separate_new_existing(transactions=filtered, user_id=user_id, db=db)
        new = separated["new"]
        existing = separated["existing"]
        logger.info(
            f"Completed new-existing transactions separation. "
            f"Total: {len(filtered)} | "
            f"New: {len(new)} | "
            f"Existing: {len(existing)}"
        )

        prepared = add_eur_amount(new)
        enriched = enrich_transactions(prepared)

        imported = import_transactions(
            transactions=enriched,
            user_id=user_id,
            job_id=job_id,
            db=db,
        )

        logger.info("Completed transaction data enrichment.")

        # Update job status in DB.
        job.imported_txn_count = len(imported)
        job.duplicate_txn_count = len(existing)
        update_job_completed(job=job, db=db)

        logger.info(
            f"Completed import job {job.id} for {job.statement_source}. "
            f"Imported {job.imported_txn_count} new transactions | "
            f"{job.duplicate_txn_count} were duplicates"
        )

        # [DEV OBSERVABILITY]
        if app_config.APP_ENVIRONMENT == AppEnvironment.DEV:
            _transactions_dump(extracted, "test_extracted")
            _transactions_dump(filtered, "filtered")
            _transactions_dump(new, "new")
            _transactions_dump(existing, "existing")
            _transactions_dump(prepared, "prepared")
            _transactions_dump(enriched, "enriched")
            _transactions_dump(imported, "imported")

    except Exception as e:
        failure_details: JobFailureDetails = get_failure_details(e)
        failure_reason = failure_details["job_failure_reason"]
        error_message = failure_details["error_message"]
        # logger.exception will output full traceback for debugging
        logger.exception(f"Job {job.id} failed. Reason: {error_message}")
        update_job_failed(job=job, db=db, failure_reason=failure_reason)


def apply_business_filter(
    transactions: Iterable[ExtractedTransaction],
    filter_rules: Iterable[FilterRuleFN] | None = None,
) -> list[ExtractedTransaction]:
    try:
        filter_rules = filter_rules or get_filter_rules()
        return [
            txn
            for txn in transactions
            if all(filter_function(txn) for filter_function in filter_rules)
        ]
    except Exception as e:
        raise BusinessRuleFilterError from e


def separate_new_existing(
    transactions: Iterable[ExtractedTransaction], user_id: UUID, db: Engine
) -> NewExistingSeparation:
    new, existing = [], []
    try:
        existing_dedup_keys = get_existing_dedup_keys(user_id=user_id, db=db)
        for transaction in transactions:
            if transaction.dedup_key not in existing_dedup_keys:
                new.append(transaction)
            else:
                existing.append(transaction)
        return {
            "new": new,
            "existing": existing,
        }
    except Exception as e:
        raise ExistingTransactionSeparationError from e


def add_eur_amount(
    transactions: Iterable[ExtractedTransaction],
    currency_converter: CurrencyConverter | None = None,
) -> list[ImportableTransaction]:
    result = []
    try:
        converter = currency_converter or CurrencyConverter(ECB_URL)
    except Exception as e:
        raise CurrencyConversionError("Could not initialize currency converter") from e

    for txn in transactions:
        eur_amount = get_eur_amount(
            converter=converter,
            txn_date=txn.transaction_datetime,
            orig_currency=txn.orig_currency,
            orig_amount=txn.orig_amount,
        )
        importable = ImportableTransaction(
            **txn.model_dump(),
            eur_amount=eur_amount,
        )
        result.append(importable)

    return result


def enrich_transactions(
    transactions: Iterable[ImportableTransaction],
) -> list[ImportableTransaction]:
    # Add spending categories and meal type to importable transactions
    for txn in transactions:
        # Spending categories only relevant for debit transactions
        if txn.side != Side.DEBIT:
            continue

        spending_categories = get_category_data(txn)
        txn.l1_category = spending_categories.get("l1_category", None)
        txn.l2_category = spending_categories.get("l2_category", None)
        txn.l3_category = spending_categories.get("l3_category", None)

        # We prefer the value from extraction source, as it's closer to truth and has richer information
        txn.note = txn.note or spending_categories.get("note")

        txn.meal_type = get_meal_type(txn, spending_categories)

    return transactions


def import_transactions(
    transactions: Iterable[ImportableTransaction],
    user_id: UUID,
    job_id: UUID,
    db: Engine,
) -> list[Transaction]:
    # Input: importable transactions, job context and DB dependency
    # Output: imported transactions in the shape of DB data model
    # Insert new transactions in the DB
    ready_to_insert = [
        convert_to_db_transaction(
            transaction=txn,
            user_id=user_id,
            job_id=job_id,
        )
        for txn in transactions
    ]

    insert_transactions(transactions=ready_to_insert, db=db)

    return ready_to_insert


def convert_to_db_transaction(
    transaction: ImportableTransaction,
    user_id: UUID,
    job_id: UUID | None = None,
    manually_added: bool = False,
) -> Transaction:
    return Transaction(
        **transaction.model_dump(),
        import_job_id=job_id,
        user_id=user_id,
        manually_added=manually_added,
    )


def update_job_failed(job: StatementImportJob, db: Engine, failure_reason: str) -> None:
    job.updated_at = dt.datetime.now()
    job.status = ImportJobStatus.FAILED
    job.failure_reason = failure_reason
    update_job(updated_job=job, db=db)


def update_job_completed(job: StatementImportJob, db: Engine) -> None:
    current_time = dt.datetime.now()
    job.completed_at = current_time
    job.updated_at = current_time
    job.status = ImportJobStatus.COMPLETED
    update_job(updated_job=job, db=db)


def update_job_start(job: StatementImportJob, db: Engine) -> None:
    current_time = dt.datetime.now()
    job.started_at = current_time
    job.updated_at = current_time
    job.status = ImportJobStatus.RUNNING
    update_job(updated_job=job, db=db)


def get_failure_details(exc: Exception) -> JobFailureDetails:
    exception_mapping = {
        CurrencyConversionError: (
            "CURRENCY_CONVERSION_ERROR",
            "Error while converting a transaction to standard currency",
        ),
        StatementDownloadError: (
            "STATEMENT_LOAD_ERROR",
            "Error while loading statement data",
        ),
        ExtractorNotFoundError: (
            "EXTRACTOR_NOT_FOUND",
            "Extractor not found for the provided statement",
        ),
        StatementExtractorError: (
            "TRANSACTIONS_EXTRACTION_ERROR",
            "Error while extracting transactions from statement",
        ),
        BusinessRuleFilterError: (
            "BUSINESS_RULE_FILTER_ERROR",
            "Error while applying business rule filters on the transactions",
        ),
        ExistingTransactionSeparationError: (
            "EXISTING_TRANSACTIONS_FILTER_ERROR",
            "Error while filtering transactions that already exist",
        ),
        TransactionInsertError: (
            "TRANSACTION_INSERT_ERROR",
            "Error while inserting new transactions",
        ),
    }
    for exception_type in exception_mapping:
        if isinstance(exc, exception_type):
            reason, message = exception_mapping[exception_type]
            return {
                "job_failure_reason": reason,
                "error_message": message,
            }

    return {
        "job_failure_reason": "OTHER_ERROR",
        "error_message": "Unexpected error",
    }

def _transactions_dump(transactions, filename):
    df = pd.DataFrame(txn.model_dump() for txn in transactions)
    logs_dir = Path.absolute(Path(__name__).parent.parent) / "throwaway" / "import_logs"
    df.to_csv(f"{logs_dir}/{filename}.csv")
