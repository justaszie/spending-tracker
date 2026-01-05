from typing import Annotated

from fastapi import Depends, Request
from sqlmodel import Session

from app.file_storage import FileStorage


def get_db_session(request: Request):
    with Session(request.app.state.db_engine) as session:
        yield session


def get_file_storage(request: Request) -> FileStorage:
    return request.app.state.file_storage


DBDependency = Annotated[Session, Depends(get_db_session)]
FSDependency = Annotated[FileStorage, Depends(get_file_storage)]
