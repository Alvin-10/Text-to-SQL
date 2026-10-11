"""Application settings, loaded from environment / .env."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url

# SQLAlchemy backend name -> sqlglot dialect
_SQLGLOT_DIALECT = {
    "postgresql": "postgres",
    "postgres": "postgres",
    "mysql": "mysql",
    "mariadb": "mysql",
}
_DIALECT_LABEL = {"postgres": "PostgreSQL", "mysql": "MySQL"}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # Database
    database_url: str = "postgresql+psycopg2://admin:admin_pw@localhost:5432/chinook"
    readonly_database_url: str = (
        "postgresql+psycopg2://readonly:readonly_pw@localhost:5432/chinook"
    )

    # LLM
    llm_provider: str = "gemini"
    llm_model: str = "gemini-3.5-flash"
    gemini_api_key: str | None = None

    # Agent / safety
    max_retries: int = 2
    query_timeout_ms: int = 5000
    max_rows: int = 100
    default_limit: int = 100
    schema_cache_path: str = ".cache/schema.json"

    @property
    def backend_name(self) -> str:
        """SQLAlchemy backend name of the read-only URL (e.g. 'postgresql')."""
        return make_url(self.readonly_database_url).get_backend_name()

    @property
    def sql_dialect(self) -> str:
        """sqlglot dialect matching the target database."""
        return _SQLGLOT_DIALECT.get(self.backend_name, "postgres")

    @property
    def sql_dialect_label(self) -> str:
        """Human name of the dialect, for the LLM prompt."""
        return _DIALECT_LABEL.get(self.sql_dialect, "SQL")


settings = Settings()
