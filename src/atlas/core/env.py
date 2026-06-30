from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict


def project_root() -> Path:
    return Path(__file__).resolve().parents[3]


load_dotenv(project_root() / ".env")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str | None = None
    binance_demo_api_key: str | None = None
    binance_demo_api_secret: str | None = None
    binance_live_api_key: str | None = None
    binance_live_api_secret: str | None = None
    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None
    discord_webhook_url: str | None = None
    alert_email_to: str | None = None
    alert_email_from: str | None = None
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_use_tls: bool = True
    alert_webhook_url: str | None = None
    atlas_kill_switch: bool = False
    atlas_api_host: str = "127.0.0.1"
    atlas_api_port: int = 8000
    atlas_cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000"

    @property
    def kill_switch_active(self) -> bool:
        from atlas.runtime.system_store import get_runtime_system

        runtime = get_runtime_system()
        if runtime.kill_switch is not None:
            return runtime.kill_switch
        raw = os.getenv("ATLAS_KILL_SWITCH", "0")
        return raw.strip().lower() in {"1", "true", "yes", "on"}

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.atlas_cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
