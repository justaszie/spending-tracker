from uuid import UUID

from pydantic_settings import BaseSettings, SettingsConfigDict

class AppSettings(BaseSettings):
    statements_bucket: str = "statements"
    test_user_id: UUID = UUID("1a35a330-2c1c-41ca-afee-0687a49b4c65")
    db_connection_string: str
    supabase_url: str
    supabase_anon_key: str
    supabase_admin_key: str

    model_config = SettingsConfigDict(env_file='.env')