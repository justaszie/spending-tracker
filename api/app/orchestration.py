from pathlib import Path
from .parsers import parse_revolut_statement

def run_job(job_id: str) -> None:
    # 1. Load job info

    # 2. Find the right parser

    # 3. Get parsed transactions

    # 4. Enhance transactions to match the DB schema (EUR, Categories, Dedup key)

    # 5. Insert new transactions

    # 6. Update job status in DB.
    print('### PARSED TRANSACTIONS ###')
    print(parse_revolut_statement(Path("abc")))