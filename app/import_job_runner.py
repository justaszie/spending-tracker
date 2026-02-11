from collections.abc import Iterable
from decimal import Decimal
from typing import TypedDict
from uuid import UUID
import datetime as dt
import logging

from currency_converter import ECB_URL, CurrencyConverter
from sqlalchemy import Engine
import pandas as pd

from app.business_rules.filters import get_filter_rules
from app.business_rules.spending_categories import CATEGORY_RULES, CategoryData
from app.core.config import AppEnvironment
from app.core.dependencies import AppConfig
from app.core.project_types import ExtractedTransaction, JobStatus, Side
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
    is_food_spending,
)
from app.statement_extractors.errors import StatementExtractorError
from app.statement_extractors.registry import get_extractor
from app.storage.file_storage import FileStorage, StatementDownloadError

logger = logging.getLogger(__name__)


class JobNotFoundError(Exception):
    pass


class ExtractorNotFoundError(Exception):
    pass


class BusinessRuleFilterError(Exception):
    pass


class ExistingTransactionFilterError(Exception):
    pass


class JobFailureDetails(TypedDict):
    job_failure_reason: str
    error_message: str


class ExistingFilterResults(TypedDict):
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
    logger.log(logging.INFO, f"### Starting Job: {job.id} for {job.statement_source}")

    try:
        # Load the statement from file storage
        statement = file_storage.load_file(
            job.file_path, bucket=app_config.STATEMENTS_STORAGE_BUCKET
        )

        # Find the right extractor for the statement
        extractor_fn = get_extractor(job.statement_source)
        if extractor_fn is None:
            raise ExtractorNotFoundError(
                f'Exractor not found for statement source: "{job.statement_source}"'
            )

        # Get extracted transactions in standard format
        extracted_txns: list[ExtractedTransaction] = extractor_fn(statement)

        # [DEV OBSERVABILITY]
        if app_config.APP_ENVIRONMENT == AppEnvironment.DEV:
            df = pd.DataFrame(txn.model_dump() for txn in extracted_txns)
            df.to_csv("test_output_extracted.csv")

        # Apply filtering rules to discard irrelevant transactions
        try:
            filtered = [
                txn
                for txn in extracted_txns
                if all(filter_function(txn) for filter_function in get_filter_rules())
            ]
        except Exception as e:
            raise BusinessRuleFilterError from e

        # [DEV OBSERVABILITY]
        if app_config.APP_ENVIRONMENT == AppEnvironment.DEV:
            df = pd.DataFrame(txn.model_dump() for txn in filtered)
            df.to_csv("test_output_filtered.csv")

        existing_filter_results = filter_existing(
            transactions=filtered, user_id=user_id, db=db
        )
        new = existing_filter_results["new"]
        existing = existing_filter_results["existing"]

        # [DEV OBSERVABILITY]
        if app_config.APP_ENVIRONMENT == AppEnvironment.DEV:
            df = pd.DataFrame(txn.model_dump() for txn in existing)
            df.to_csv("test_duplicates.csv")

        enriched = []
        # Enrich transactions data to match the DB schema
        # TODO - potential failure already when getting converter
        ccy_converter = CurrencyConverter(ECB_URL)
        for transaction in new:
            eur_amount = get_eur_amount(
                converter=ccy_converter,
                txn_date=transaction.transaction_datetime,
                orig_currency=transaction.orig_currency,
                orig_amount=transaction.orig_amount,
            )

            # Spending categories only relevant for debit transactions
            spending_categories = (
                get_category_data(transaction, eur_amount, CATEGORY_RULES)
                if transaction.side == Side.DEBIT
                else {}
            )

            # Calculating meal type for food transactions only
            meal_type = (
                get_meal_type(transaction, spending_categories)
                if is_food_spending(spending_categories)
                else None
            )

            enriched.append(
                convert_to_db_transaction(
                    transaction=transaction,
                    eur_amount=eur_amount,
                    spending_categories=spending_categories,
                    meal_type=meal_type,
                    user_id=user_id,
                    job_id=job_id,
                )
            )

        # [DEV OBSERVABILITY]
        if app_config.APP_ENVIRONMENT == AppEnvironment.DEV:
            df = pd.DataFrame(txn.model_dump() for txn in enriched)
            df.to_csv("test_output_enriched.csv")

        # Insert new transactions in the DB
        insert_transactions(transactions=enriched, db=db)

        # Update job status in DB.
        job.imported_txn_count = len(enriched)
        job.duplicate_txn_count = len(existing)
        update_job_completed(job=job, db=db)

        logger.log(
            logging.INFO, f"### Completed Job: {job.id} for {job.statement_source}"
        )
        logger.log(
            logging.INFO,
            f"Imported {job.imported_txn_count} new transactions | {job.duplicate_txn_count} duplicates",
        )

    except Exception as e:
        failure_details: JobFailureDetails = get_failure_details(e)
        failure_reason = failure_details["job_failure_reason"]
        error_message = failure_details["error_message"]
        # logger.exception will output full traceback for debugging
        logger.exception(f"Job {job.id} failed. Reason: {error_message}")
        update_job_failed(job=job, db=db, failure_reason=failure_reason)


def filter_existing(
    transactions: Iterable[ExtractedTransaction], user_id: UUID, db: Engine
) -> ExistingFilterResults:
    new, existing = [], []
    try:
        # Using set for O(1) lookups
        existing_dedup_keys = set(get_existing_dedup_keys(user_id=user_id, db=db))
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
        raise ExistingTransactionFilterError from e


def convert_to_db_transaction(
    transaction: ExtractedTransaction,
    eur_amount: Decimal,
    spending_categories: CategoryData,
    user_id: UUID,
    meal_type: str | None = None,
    job_id: UUID | None = None,
    manually_added: bool = False,
) -> Transaction:
    # free textn notes can be either populated from the source or by categorization logic.
    # We prefer the source value as it's closer to truth and has richer information
    transaction_note = transaction.note or spending_categories.get("note")

    return Transaction(
        transaction_datetime=transaction.transaction_datetime,
        type=transaction.type,
        counterparty=transaction.counterparty,
        orig_amount=transaction.orig_amount,
        orig_currency=transaction.orig_currency,
        side=transaction.side,
        source=transaction.source,
        dedup_key=transaction.dedup_key,
        eur_amount=eur_amount,
        l1_category=spending_categories.get("l1_category"),
        l2_category=spending_categories.get("l2_category"),
        l3_category=spending_categories.get("l3_category"),
        note=transaction_note,
        meal_type=meal_type,
        import_job_id=job_id,
        user_id=user_id,
        manually_added=manually_added,
    )


def update_job_failed(job: StatementImportJob, db: Engine, failure_reason: str) -> None:
    job.updated_at = dt.datetime.now()
    job.status = JobStatus.FAILED
    job.failure_reason = failure_reason
    update_job(updated_job=job, db=db)


def update_job_completed(job: StatementImportJob, db: Engine) -> None:
    current_time = dt.datetime.now()
    job.completed_at = current_time
    job.updated_at = current_time
    job.status = JobStatus.COMPLETED
    update_job(updated_job=job, db=db)


def update_job_start(job: StatementImportJob, db: Engine) -> None:
    current_time = dt.datetime.now()
    job.started_at = current_time
    job.updated_at = current_time
    job.status = JobStatus.RUNNING
    update_job(updated_job=job, db=db)


def get_failure_details(exc: Exception) -> JobFailureDetails:
    exception_mapping = {
        CurrencyConversionError: (
            "CURRENCY_CONVERSION_ERROR",
            "Errorw hile converting a transaction to standard currency",
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
        ExistingTransactionFilterError: (
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
