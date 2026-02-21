from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class PostgresConfig:
    host: str
    port: int
    db: str
    user: str
    password: str

    @classmethod
    def from_env(cls) -> PostgresConfig:
        return cls(
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=int(os.getenv("POSTGRES_PORT", "5432")),
            db=os.getenv("POSTGRES_DB", "tgsys"),
            user=os.getenv("POSTGRES_USER", "postgres"),
            password=os.getenv("POSTGRES_PASSWORD", "password"),
        )


@dataclass
class KafkaConfig:
    broker: str
    topic: str
    consumer_group: str
    consumer_start_delay: int = 20

    @classmethod
    def from_env(cls) -> KafkaConfig:
        return cls(
            broker=os.getenv("KAFKA_BROKER", "localhost:9092"),
            topic=os.getenv("KAFKA_TOPIC", "telegram-last-post"),
            consumer_group=os.getenv("KAFKA_CONSUMER_GROUP", "task-distributor-group"),
            consumer_start_delay=int(os.getenv("KAFKA_CONSUMER_START_DELAY", "20")),
        )


@dataclass
class AppConfig:
    log_level: str = "INFO"
    min_health_score: int = 70
    cooldown_minutes: float = 18.0  # Changed to minutes (was 0.3 hours)
    max_retries: int = 3
    retry_delay: int = 5  # seconds

    @classmethod
    def from_env(cls) -> AppConfig:
        return cls(
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            min_health_score=int(os.getenv("MIN_HEALTH_SCORE", "70")),
            cooldown_minutes=float(os.getenv("COOLDOWN_MINUTES", "2")),  # Changed env var name
            max_retries=int(os.getenv("MAX_RETRIES", "3")),
            retry_delay=int(os.getenv("RETRY_DELAY", "5")),
        )


def setup_logging() -> None:
    """Configure logging for the application."""
    import logging
    import sys
    
    log_level = os.getenv("LOG_LEVEL", "INFO")
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
        ]
    )
