from enum import StrEnum
from uuid import UUID

from pydantic_settings import BaseSettings, SettingsConfigDict

class AppEnvironment(StrEnum):
    DEV = "DEV"
    PROD = "PROD"


class AppConfig(BaseSettings):
    statements_storage_bucket: str = "statements"
    test_user_id: UUID
    app_environment: AppEnvironment = AppEnvironment.PROD
    db_connection_string: str
    supabase_url: str
    supabase_anon_key: str
    supabase_admin_key: str

    model_config = SettingsConfigDict(env_file='.env')