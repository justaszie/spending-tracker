import logging
import openpyxl

from uuid import UUID, uuid4
from typing import Annotated, Literal

from fastapi import FastAPI, File, Form, UploadFile
from pydantic import BaseModel

logging.basicConfig(
    format="[{levelname}] - {asctime} - {name}: {message}",
    style="{",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

app = FastAPI()

type JobStatus = Literal["pending", "complete"]
type JobType = Literal["ingest"]


class JobCreateResponse(BaseModel):
    job_type: JobType
    job_id: UUID
    status: JobStatus


@app.get("/")
def root() -> "str":
    return "HELLO FROM SPENDING TRACKER"


@app.post("/job")
def create_job(statement_file: UploadFile) -> JobCreateResponse:
    book = openpyxl.load_workbook(statement_file.file, data_only=True)
    logger.info(f"EXCEL: {book.worksheets[0]}")
    return JobCreateResponse(job_type="ingest", status="pending", job_id=uuid4())