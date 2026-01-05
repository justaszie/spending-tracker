from pathlib import Path
from uuid import UUID

import openpyxl
from sqlalchemy import Engine
from sqlmodel import Session

from app.file_storage import FileStorage
from app.jobs import load_job
from app.parsers import get_parser

def run_job(job_id: str, db_engine: Engine, file_storage: FileStorage) -> None:
    with Session(db_engine) as session:
        # 1. Load job info
        job = load_job(UUID(job_id), session)

        # 2. Load the statement from file storage
        statement = file_storage.load_file(job.file_path)

        # 3. Find the right parser
        parser = get_parser(job.bank)

        # 4. Get parsed transactions
        txns = parser(file=statement)

        # 5. Enhance transactions to match the DB schema (EUR, Categories, Dedup key)

        # 6. Insert new transactions

        # 7. Update job status in DB.

        # 8. Log the results
        print('### PARSED TRANSACTIONS ###')
        # print(parse_revolut_statement(Path("abc")))