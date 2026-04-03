from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "aibotchat"
    app_env: str = "local"
    app_debug: bool = False
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    app_auto_create_tables: bool = True

    database_url: str | None = Field(default=None, alias="DATABASE_URL")

    postgres_host: str = "127.0.0.1"
    postgres_port: int = 5432
    postgres_db: str = "aibotchat"
    postgres_user: str = "postgres"
    postgres_password: str = "postgres"

    redis_host: str = "127.0.0.1"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str | None = None

    log_level: str = "INFO"

    # LLM
    llm_provider: str = "openai"
    llm_api_key: str = ""
    llm_base_url: str = "https://api.openai.com/v1"
    llm_default_model: str = "gpt-4o-mini"
    llm_timeout: float = 60.0
    llm_max_context_rounds: int = 20

    # Guards / Rate Limiting
    guard_max_requests_per_minute: int = 20
    guard_max_message_length: int = 4000
    guard_session_lock_enabled: bool = True
    guard_idempotency_enabled: bool = True
    guard_idempotency_ttl: int = 300

    @property
    def resolved_database_url(self) -> str:
        if self.database_url:
            return self.database_url

        if self.postgres_host and self.postgres_db and self.postgres_user:
            return (
                "postgresql+psycopg://"
                f"{self.postgres_user}:{self.postgres_password}"
                f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
            )

        return "sqlite:///./aibotchat.db"

    @property
    def resolved_redis_url(self) -> str:
        auth = ""
        if self.redis_password:
            auth = f":{self.redis_password}@"

        return f"redis://{auth}{self.redis_host}:{self.redis_port}/{self.redis_db}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
