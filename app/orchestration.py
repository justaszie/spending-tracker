import datetime as dt
from decimal import Decimal
import logging
from uuid import UUID

from currency_converter import ECB_URL, CurrencyConverter
import pandas as pd
from sqlalchemy import Engine

from app.category_rules import CATEGORY_RULES, CategoryData
from app.config import AppEnvironment
from app.db.jobs import load_job, update_job
from app.db.transactions import (
    Transaction,
    get_existing_dedup_keys,
    insert_transactions,
)
from app.dependencies import AppConfig
from app.enrichment import (
    get_category_data,
    get_eur_amount,
    get_meal_type,
    is_food_spending,
)
from app.file_storage import FileStorage
from app.filters import filter_transactions
from app.parsers.registry import get_parser
from app.project_types import ImportedTransaction, JobStatus

logger = logging.getLogger(__name__)


def run_job(
    job_id: UUID,
    user_id: UUID,
    db: Engine,
    file_storage: FileStorage,
    app_config: AppConfig,
) -> None:
    # 1. Load job info
    job = load_job(job_id, db)
    if not job:
        return

    logger.log(logging.INFO, f"### Starting Job: {job.id} for {job.statement_source}")
    job.started_at = dt.datetime.now()
    job.status = JobStatus.RUNNING
    update_job(updated_job=job, db=db)

    # Load the statement from file storage
    statement = file_storage.load_file(
        job.file_path, bucket=app_config.statements_storage_bucket
    )

    # Find the right parser
    parser = get_parser(job.statement_source)

    # Log it and update job record status=failed, reason=technical_error
    if parser is None:
        return

    # 4. Get imported transactions
    imported_txns: list[ImportedTransaction] = parser(statement)

    # [DEV OBSERVABILITY]
    if app_config.app_environment == AppEnvironment.DEV:
        df = pd.DataFrame(txn.model_dump() for txn in imported_txns)
        df.to_csv("test_output_imported.csv")

    filtered = filter_transactions(imported_txns)

    # [DEV OBSERVABILITY]
    if app_config.app_environment == AppEnvironment.DEV:
        df = pd.DataFrame(txn.model_dump() for txn in filtered)
        df.to_csv("test_output_filtered.csv")

    new: list[ImportedTransaction] = []
    duplicates: list[ImportedTransaction] = []

    # Using set for O(1) lookups
    existing_dedup_keys = set(get_existing_dedup_keys(db=db))
    for transaction in filtered:
        if transaction.dedup_key not in existing_dedup_keys:
            new.append(transaction)
        else:
            duplicates.append(transaction)

    # [DEV OBSERVABILITY]
    if app_config.app_environment == AppEnvironment.DEV:
        df = pd.DataFrame(txn.model_dump() for txn in duplicates)
        df.to_csv("test_duplicates.csv")

    # TODO - move enrichment logic here:
    # 1. Call pure enrichment functions to get pieces of data:
    #   eur, categories, meal_type (if food),
    # 2. Set job and user_id context
    # 3. Map the ImportedTransaction values and new values to target Transaction model

    enriched = []
    # 5. Enhance transactions to match the DB schema (EUR, Categories, Dedup key)
    ccy_converter = CurrencyConverter(ECB_URL)
    for transaction in new:
        eur_amount = get_eur_amount(
            converter=ccy_converter,
            txn_date=transaction.transaction_datetime,
            orig_currency=transaction.orig_currency,
            orig_amount=transaction.orig_amount,
        )

        spending_categories = get_category_data(transaction, CATEGORY_RULES)

        meal_type = None
        if is_food_spending(spending_categories):
            meal_type = get_meal_type(transaction, spending_categories)

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
    if app_config.app_environment == AppEnvironment.DEV:
        df = pd.DataFrame(txn.model_dump() for txn in enriched)
        df.to_csv("test_output_enriched.csv")

    # 7. Insert new transactions
    insert_transactions(transactions=enriched, db=db)

    # 8. Update job status in DB.
    job.finished_at = dt.datetime.now()
    job.status = JobStatus.COMPLETED
    job.ingested_txn_count = len(enriched)
    job.duplicate_txn_count = len(duplicates)

    update_job(updated_job=job, db=db)

    logger.log(logging.INFO, f"### Completed Job: {job.id} for {job.statement_source}")
    logger.log(
        logging.INFO,
        f"Inserted {job.ingested_txn_count} new transactions | {job.duplicate_txn_count} duplicates",
    )


def convert_to_db_transaction(
    transaction: ImportedTransaction,
    eur_amount: Decimal,
    spending_categories: CategoryData,
    user_id: UUID,
    meal_type: str | None = None,
    job_id: UUID | None = None,
    manually_added: bool = False,
) -> Transaction:
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
        note=spending_categories.get("note"),
        meal_type=meal_type,
        job_id=job_id,
        user_id=user_id,
        manually_added=manually_added,
    )
