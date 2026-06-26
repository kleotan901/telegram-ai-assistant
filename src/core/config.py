from pydantic import PostgresDsn, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Telegram ──────────────────────────────────
    bot_token: str
    webhook_url: str = ""

    # ── PostgreSQL  ──────────────────────────────
    postgres_db: str = "ai_assistant"
    postgres_user: str = "postgres"
    postgres_password: str
    postgres_host: str = "db"
    postgres_port: int = 5432

    # ── External AI API ───────────────────────────────────────
    ai_api_url: str
    ai_api_key: str = ""

    # ── App ───────────────────────────────────────────────────
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    debug: bool = False

    # ── Computed fields (обчислюються автоматично) ────────────
    @computed_field
    @property
    def database_url(self) -> str:
        """
        Асинхронний URL для SQLAlchemy + asyncpg.
        Формат: postgresql+asyncpg://user:password@host:port/dbname
        """
        return (
            f"postgresql+asyncpg://"
            f"{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}"
            f"/{self.postgres_db}"
        )

    @computed_field
    @property
    def database_url_sync(self) -> str:
        """
        Синхронний URL для Alembic міграцій.
        Alembic не підтримує asyncpg напряму, тому - psycopg2 (синхронний драйвер).
        """
        return (
            f"postgresql+psycopg2://"
            f"{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}"
            f"/{self.postgres_db}"
        )

settings = Settings()
