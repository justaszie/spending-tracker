import datetime as dt
import uuid
from typing import Literal

from pydantic import BaseModel, Field

type Bank = Literal["swedbank_lt", "revolut"]
type JobStatus = Literal["pending", "complete"]

class ConfigException(Exception):
    pass