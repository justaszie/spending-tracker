import datetime as dt
from dataclasses import dataclass


@dataclass
class Transaction:
    started_at: dt.datetime
    amount_cents: int
    currency: str


