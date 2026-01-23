from functools import lru_cache
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy import Engine

from app.file_storage import FileStorage
from app.config import AppSettings


def get_db_engine(request: Request):
    return request.app.state.db_engine


def get_file_storage(request: Request) -> FileStorage:
    return request.app.state.file_storage

# Settings singleton will be stored in cache and reused for every request
@lru_cache
def get_settings() -> AppSettings:
    # Ignoring type checking. Type checker expects config variables passed as args
    # but they are being read from environment.
    return AppSettings() # type: ignore


DBDependency = Annotated[Engine, Depends(get_db_engine)]
FSDependency = Annotated[FileStorage, Depends(get_file_storage)]
SettingsDependency = Annotated[AppSettings, Depends(get_settings)]