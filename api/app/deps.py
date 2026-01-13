from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy import Engine
from sqlmodel import Session

from app.file_storage import FileStorage


def get_db_engine(request: Request):
    return request.app.state.db_engine


def get_file_storage(request: Request) -> FileStorage:
    return request.app.state.file_storage


DBDependency = Annotated[Engine, Depends(get_db_engine)]
FSDependency = Annotated[FileStorage, Depends(get_file_storage)]
