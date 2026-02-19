from __future__ import annotations

import logging
import os
from dataclasses import dataclass


def setup_logging() -> None:
    """Configure logging for the application."""
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


@dataclass(frozen=True)
class PostgresConfig:
    host: str
    port: int
    db: str
    user: str
    password: str

    @classmethod
    def from_env(cls) -> "PostgresConfig":
        host = os.getenv("POSTGRES_HOST", "postgres")
        port = int(os.getenv("POSTGRES_PORT", "5432"))
        db = os.getenv("POSTGRES_DB", "mydb")
        user = os.getenv("POSTGRES_USER", "user")
        password = os.getenv("POSTGRES_PASSWORD", "password")

        return cls(host=host, port=port, db=db, user=user, password=password)


@dataclass(frozen=True)
class KafkaConfig:
    broker: str
    topic: str
    consumer_group: str
    start_delay: int

    @classmethod
    def from_env(cls) -> "KafkaConfig":
        broker = os.getenv("KAFKA_BROKER", "kafka:9092")
        topic = os.getenv("KAFKA_TOPIC", "telegram-last-post")
        consumer_group = os.getenv("KAFKA_CONSUMER_GROUP", "post-commenter-group")
        start_delay = int(os.getenv("KAFKA_CONSUMER_START_DELAY", "25"))

        return cls(
            broker=broker,
            topic=topic,
            consumer_group=consumer_group,
            start_delay=start_delay,
        )


@dataclass(frozen=True)
class WorkerConfig:
    sessions_dir: str
    min_cooldown_minutes: int
    max_cooldown_minutes: int
    max_workers: int
    worker_timeout: int

    @classmethod
    def from_env(cls) -> "WorkerConfig":
        sessions_dir = os.getenv("SESSIONS_DIR", "/app/sessions")
        min_cooldown_minutes = int(os.getenv("MIN_COOLDOWN_MINUTES", "10"))
        max_cooldown_minutes = int(os.getenv("MAX_COOLDOWN_MINUTES", "30"))
        max_workers = int(os.getenv("MAX_WORKERS", "50"))
        worker_timeout = int(os.getenv("WORKER_TIMEOUT", "300"))

        return cls(
            sessions_dir=sessions_dir,
            min_cooldown_minutes=min_cooldown_minutes,
            max_cooldown_minutes=max_cooldown_minutes,
            max_workers=max_workers,
            worker_timeout=worker_timeout,
        )


@dataclass(frozen=True)
class AppConfig:
    log_level: str

    @classmethod
    def from_env(cls) -> "AppConfig":
        log_level = os.getenv("LOG_LEVEL", "INFO")
        return cls(log_level=log_level)
