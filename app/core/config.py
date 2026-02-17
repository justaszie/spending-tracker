from enum import StrEnum
from uuid import UUID

from pydantic_settings import BaseSettings, SettingsConfigDict


class AppEnvironment(StrEnum):
    DEV = "DEV"
    PROD = "PROD"


class AppConfig(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    STATEMENTS_STORAGE_BUCKET: str = "statements"
    TEST_USER_ID: UUID | None = None
    APP_ENVIRONMENT: AppEnvironment = AppEnvironment.PROD
    DB_CONNECTION_STRING: str
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_ADMIN_KEY: str
    MAX_STATEMENT_SIZE: int = 2 * 1024**2 # 2MB based on the available samples
    V1_API_PREFIX: str = "/api/v1"
    FRONTEND_URL: str | None = None
