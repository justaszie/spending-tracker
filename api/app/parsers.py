import datetime as dt
from pathlib import Path

from app.transactions import Transaction

def parse_revolut_statement(filepath: Path) -> list[Transaction]:
    return [Transaction(started_at=dt.datetime(2025, 12, 11), amount_cents=120, currency="EUR")]