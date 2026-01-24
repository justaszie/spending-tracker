import datetime as dt
import logging
from uuid import UUID

import pandas as pd
from sqlalchemy import Engine

from app.file_storage import FileStorage
from app.db.jobs import load_job, update_job
from app.db.transactions import (
    get_existing_dedup_keys,
    insert_transactions,
    Transaction,
)
from app.dependencies import AppConfig
from app.parsers.registry import get_parser
from app.project_types import JobStatus, ParsedTransaction
from app.enrichment import enrich_transactions

logger = logging.getLogger(__name__)


def run_job(job_id: str, db: Engine, file_storage: FileStorage, app_config: AppConfig) -> None:
    # 1. Load job info
    job_uuid = UUID(job_id)
    job = load_job(job_uuid, db)
    if not job:
        return

    logger.log(logging.INFO, f"### Starting Job: {job.id} for {job.statement_source}")
    job.started_at = dt.datetime.now()
    job.status = JobStatus.RUNNING
    update_job(updated_job=job, db=db)

    # Load the statement from file storage
    statement = file_storage.load_file(job.file_path, bucket=app_config.statements_storage_bucket)

    # Find the right parser
    parser = get_parser(job.statement_source)

    # Log it and update job record status=failed, reason=technical_error
    if parser is None:
        return

    # 4. Get parsed transactions
    parsed_txns: list[ParsedTransaction] = parser(statement)

    # [DEV OBSERVABILITY]
    df = pd.DataFrame(txn.model_dump() for txn in parsed_txns)
    df.to_csv("test_output_parsed.csv")

    # 5. Enhance transactions to match the DB schema (EUR, Categories, Dedup key)
    enriched = enrich_transactions(parsed_txns, job_id=job_uuid)
    df = pd.DataFrame(txn.model_dump() for txn in enriched)
    df.to_csv("test_output_enriched.csv")

    new: list[Transaction] = []
    duplicates: list[Transaction] = []

    # Using set for O(1) lookups
    existing_dedup_keys = set(get_existing_dedup_keys(db=db))
    for transaction in enriched:
        if transaction.dedup_key not in existing_dedup_keys:
            new.append(transaction)
        else:
            duplicates.append(transaction)

    # [DEV OBSERVABILITY]
    df = pd.DataFrame(txn.model_dump() for txn in duplicates)
    df.to_csv("test_duplicates.csv")

    # 7. Insert new transactions
    insert_transactions(transactions=new, db=db)
    logger.log(
        logging.INFO,
        f"Inserted {len(new)} new transactions | {len(duplicates)} duplicates",
    )

    # 8. Update job status in DB.
    job.finished_at = dt.datetime.now()
    job.status = JobStatus.COMPLETE
    job.ingested_txn_count = len(new)
    job.duplicate_txn_count = len(duplicates)

    update_job(updated_job=job, db=db)

    logger.log(logging.INFO, f"### Completed Job: {job.id} for {job.statement_source}")
