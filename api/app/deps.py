import logging
from functools import lru_cache
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Request
from fastapi.security import (
    HTTPBasic,
    HTTPBasicCredentials,
    HTTPBearer,
    HTTPAuthorizationCredentials,
)
from supabase_auth.errors import AuthApiError
from sqlalchemy import Engine

from app.file_storage import FileStorage
from app.config import AppSettings

logger = logging.getLogger(__name__)
jwt_auth = HTTPBearer()
user_creds_auth = HTTPBasic()


# Validate username (email) and password, sign user in and return a JWT token if successful
def validate_user_creds(
    request: Request, creds: Annotated[HTTPBasicCredentials, Depends(user_creds_auth)]
) -> str:
    supabase_client = request.app.state.supabase
    response = supabase_client.auth.sign_in_with_password(
        {
            "email": creds.username,
            "password": creds.password,
        }
    )
    # return response ["session"]["access_token"]
    return response.session.access_token


def get_authenticated_user(
    request: Request, header: Annotated[HTTPAuthorizationCredentials, Depends(jwt_auth)]
) -> UUID:
    token = header.credentials
    supabase_client = request.app.state.supabase
    try:
        result = supabase_client.auth.get_user(token)
    except AuthApiError as e:
        logger.log(logging.WARNING, f"Could not validate Bearer token: {e}")
        raise HTTPException(status_code=401, detail="User Authentication Failed")
    if not result:
        logger.log(logging.WARNING, "User matching Bearer token not found")
        raise HTTPException(status_code=401, detail="User Authentication Failed")

    return result.user.id


def get_db_engine(request: Request):
    return request.app.state.db_engine


def get_file_storage(request: Request) -> FileStorage:
    return request.app.state.file_storage


# Settings singleton will be stored in cache and reused for every request
@lru_cache
def get_settings() -> AppSettings:
    # Ignoring type checking. Type checker expects config variables passed as args
    # but they are being read from environment.
    return AppSettings()  # type: ignore


DBDependency = Annotated[Engine, Depends(get_db_engine)]
FSDependency = Annotated[FileStorage, Depends(get_file_storage)]
SettingsDependency = Annotated[AppSettings, Depends(get_settings)]
AuthDependency = Annotated[UUID, Depends(get_authenticated_user)]
