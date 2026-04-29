"""Environment settings loader. Values come from .env (gitignored)."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


def _split_csv(value: str | None, default: list[str]) -> list[str]:
    if not value:
        return default
    return [item.strip() for item in value.split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    env: str = field(default_factory=lambda: os.getenv("ENV", "dev"))
    cors_origins: list[str] = field(
        default_factory=lambda: _split_csv(
            os.getenv("CORS_ORIGINS"), ["http://localhost:5173"]
        )
    )
    gemini_api_key: str = field(default_factory=lambda: os.getenv("GEMINI_API_KEY", ""))
    gemini_model: str = field(
        default_factory=lambda: os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    )
    google_client_id: str = field(
        default_factory=lambda: os.getenv("GOOGLE_CLIENT_ID", "")
    )
    google_client_secret: str = field(
        default_factory=lambda: os.getenv("GOOGLE_CLIENT_SECRET", "")
    )
    google_redirect_uri: str = field(
        default_factory=lambda: os.getenv(
            "GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/google/callback"
        )
    )
    encryption_key: str = field(
        default_factory=lambda: os.getenv("ENCRYPTION_KEY", "")
    )
    database_url: str = field(
        default_factory=lambda: os.getenv("DATABASE_URL", "sqlite:///./jarvis.db")
    )
    sandbox_dir: str = field(
        default_factory=lambda: os.getenv("JARVIS_SANDBOX_DIR", "/tmp/jarvis_sandbox")
    )
    journal_reporter_url: str = field(
        default_factory=lambda: os.getenv("JOURNAL_REPORTER_URL", "")
    )
    journal_reporter_key: str = field(
        default_factory=lambda: os.getenv("JOURNAL_REPORTER_KEY", "")
    )

    @property
    def sqlite_path(self) -> str:
        """File path for the local SQLite DB."""
        prefix = "sqlite:///"
        if self.database_url.startswith(prefix):
            return self.database_url[len(prefix):]
        return self.database_url


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
