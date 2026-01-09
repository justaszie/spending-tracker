from uuid import UUID

import pandas as pd
from sqlalchemy import Engine
from sqlmodel import Session

from app.file_storage import FileStorage
from app.db.jobs import load_job
from app.parsers.registry import get_parser
from app.project_types import ParsedTransaction
from app.transformation import enhance_transactions



def run_job(job_id: str, db_engine: Engine, file_storage: FileStorage) -> None:
    with Session(db_engine) as session:
        # 1. Load job info
        job = load_job(UUID(job_id), session)
        if not job:
            return

        print(f"### Starting Job: {job.job_id} for {job.bank}")
        # Load the statement from file storage
        statement = file_storage.load_file(job.file_path)

        # Find the right parser
        parser = get_parser(job.bank)

        # TODO: how to deal when right parser not found
        # Log it and update job record status=failed, reason=technical_error
        if not parser:
            return

        # 4. Get parsed transactions
        parsed_txns: list[ParsedTransaction] = parser(statement)

        # TODO: TESTING to observe data
        df = pd.DataFrame(txn.model_dump() for txn in parsed_txns)
        df.to_csv('test_output.csv')

        # 5. Enhance transactions to match the DB schema (EUR, Categories, Dedup key)
        enhanced = enhance_transactions(parsed_txns)

        # 6. Insert new transactions
        #TODO: Check how to convert the enum values to actual strings before inserting

        # 7. Update job status in DB.

        # 8. Log the results
        print('### PARSED TRANSACTIONS ###')
        # print(parse_revolut_statement(Path("abc")))