from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class PostgresConfig:
    host: str
    port: int
    db: str
    user: str
    password: str

    @classmethod
    def from_env(cls) -> "PostgresConfig":
        host = os.getenv("POSTGRES_HOST", "localhost")
        port = int(os.getenv("POSTGRES_PORT", "5432"))
        db = os.getenv("POSTGRES_DB", "")
        user = os.getenv("POSTGRES_USER", "")
        password = os.getenv("POSTGRES_PASSWORD", "")

        missing = [
            k
            for k, v in (
                ("POSTGRES_DB", db),
                ("POSTGRES_USER", user),
                ("POSTGRES_PASSWORD", password),
            )
            if not v
        ]
        if missing:
            raise RuntimeError(f"Missing required Postgres env vars: {', '.join(missing)}")

        return cls(host=host, port=port, db=db, user=user, password=password)


@dataclass(frozen=True)
class TelegramConfig:
    api_id: int
    api_hash: str
    session_path: str

    @classmethod
    def from_env(cls) -> "TelegramConfig":
        api_id_raw = os.getenv("TRACKER_API_ID", "")
        api_hash = os.getenv("TRACKER_API_HASH", "")
        api_id = int(api_id_raw) if api_id_raw else 0
        
        # Generate session path using API_ID
        default_session_path = f"/sessions/{api_id}_session.session"
        session_path = os.getenv("TELEGRAM_SESSION_PATH", default_session_path)

        if not api_id_raw or not api_hash:
            raise RuntimeError("Missing TRACKER_API_ID / TRACKER_API_HASH in environment")

        return cls(api_id=api_id, api_hash=api_hash, session_path=session_path)


@dataclass(frozen=True)
class AppConfig:
    tick_seconds: float

    @classmethod
    def from_env(cls) -> "AppConfig":
        return cls(tick_seconds=float(os.getenv("APP_TICK_SECONDS", "3")))

