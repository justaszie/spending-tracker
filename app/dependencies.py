import logging
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Request
from fastapi.security import (
    HTTPBearer,
    HTTPAuthorizationCredentials,
)
from supabase import Client
from supabase_auth.errors import AuthApiError
from sqlalchemy import Engine

from app.file_storage import FileStorage
from app.config import AppConfig

logger = logging.getLogger(__name__)
jwt_auth = HTTPBearer()


def get_app_config(request: Request) -> AppConfig:
    return request.app.state.app_config


ConfigDependency = Annotated[AppConfig, Depends(get_app_config)]


def get_db_engine(request: Request):
    return request.app.state.db_engine


DBDependency = Annotated[Engine, Depends(get_db_engine)]


def get_file_storage(request: Request) -> FileStorage:
    return request.app.state.file_storage


FSDependency = Annotated[FileStorage, Depends(get_file_storage)]


def get_supabase_admin(request: Request) -> Client:
    return request.app.state.supabase_admin


SupabaseAdminDependency = Annotated[Client, Depends(get_supabase_admin)]


def get_authenticated_user(
    supabase_admin: SupabaseAdminDependency,
    header: Annotated[HTTPAuthorizationCredentials, Depends(jwt_auth)],
) -> UUID:
    token = header.credentials
    try:
        result = supabase_admin.auth.get_user(token)
    except AuthApiError as e:
        logger.log(logging.WARNING, f"Could not validate Bearer token: {e}")
        raise HTTPException(status_code=401, detail="User Authentication Failed")
    if not result:
        logger.log(logging.WARNING, "User matching Bearer token not found")
        raise HTTPException(status_code=401, detail="User Authentication Failed")

    return UUID(result.user.id)


AuthDependency = Annotated[UUID, Depends(get_authenticated_user)]
