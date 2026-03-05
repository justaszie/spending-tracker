from typing import Annotated, cast
from uuid import UUID
import logging

from fastapi import Depends, HTTPException, Request
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)
from sqlalchemy import Engine
from supabase_auth.errors import AuthApiError

from app.core.config import AppEnvironment, ConfigError, app_config
from app.storage.file_storage import FileStorage
from supabase import Client

logger = logging.getLogger(__name__)
jwt_auth = HTTPBearer(auto_error=False)


def get_db_engine(request: Request) -> Engine:
    return cast(Engine, request.app.state.db_engine)


DBDependency = Annotated[Engine, Depends(get_db_engine)]


def get_file_storage(request: Request) -> FileStorage:
    return cast(FileStorage, request.app.state.file_storage)


FSDependency = Annotated[FileStorage, Depends(get_file_storage)]


def get_supabase_admin(request: Request) -> Client:
    return cast(Client, request.app.state.supabase_admin)


SupabaseAdminDependency = Annotated[Client, Depends(get_supabase_admin)]


def get_authenticated_user(
    supabase_admin: SupabaseAdminDependency,
    header: Annotated[HTTPAuthorizationCredentials | None, Depends(jwt_auth)],
) -> UUID:
    # Skip jwt validation in DEV environment
    if app_config.APP_ENVIRONMENT == AppEnvironment.DEV:
        if not app_config.TEST_USER_ID:
            raise ConfigError("Missing TEST_USER_ID environment value")

        return app_config.TEST_USER_ID

    if not header:
        logger.warning("Invalid Authorization header")
        raise HTTPException(status_code=401, detail="User Authentication Failed")

    token = header.credentials
    try:
        result = supabase_admin.auth.get_user(token)
    except AuthApiError as e:
        logger.warning(f"Could not validate Bearer token: {e}")
        raise HTTPException(status_code=401, detail="User Authentication Failed") from e

    if not result:
        logger.warning("User matching Bearer token not found")
        raise HTTPException(status_code=401, detail="User Authentication Failed")

    return UUID(result.user.id)


AuthDependency = Annotated[UUID, Depends(get_authenticated_user)]
