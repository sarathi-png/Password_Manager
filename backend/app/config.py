from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Vault"
    environment: str = "development"
    database_url: str = f"sqlite:///{BASE_DIR / 'data' / 'vault.db'}"
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 720
    vault_master_key: str = ""
    master_key_file: str = str(BASE_DIR / "data" / "master.key")
    cors_origins: str = "*"
    initial_admin_username: str = "admin"
    initial_admin_password: str = "admin"
    sync_admin_password: bool = False
    rate_limit_login_per_minute: int = 10
    rate_limit_api_per_minute: int = 300
    max_import_rows: int = 50000
    opencode_api_key: str = ""
    opencode_api_base: str = "https://api.openai.com/v1"
    opencode_model: str = "gpt-4o-mini"

    @property
    def cors_origin_list(self) -> list[str]:
        if self.cors_origins.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()