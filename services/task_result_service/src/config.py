from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class KafkaConfig:
    broker: str
    result_topic: str
    task_topic: str
    consumer_group: str
    consumer_start_delay: int = 20

    @classmethod
    def from_env(cls) -> KafkaConfig:
        return cls(
            broker=os.getenv("KAFKA_BROKER", "localhost:9092"),
            result_topic=os.getenv("KAFKA_RESULT_TOPIC", "task-results"),
            task_topic=os.getenv("KAFKA_TOPIC", "comment-tasks"),
            consumer_group=os.getenv("KAFKA_CONSUMER_GROUP", "result-processor"),
            consumer_start_delay=int(os.getenv("KAFKA_CONSUMER_START_DELAY", "20")),
        )


@dataclass
class PostgresConfig:
    host: str
    port: int
    db: str
    user: str
    password: str

    @classmethod
    def from_env(cls) -> "PostgresConfig":
        return cls(
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=int(os.getenv("POSTGRES_PORT", "5432")),
            db=os.getenv("POSTGRES_DB", "telegram"),
            user=os.getenv("POSTGRES_USER", "user"),
            password=os.getenv("POSTGRES_PASSWORD", "password"),
        )

    def to_connection(self) -> "PostgresConnection":
        from postgres.client import PostgresConnection
        return PostgresConnection(
            host=self.host,
            port=self.port,
            db=self.db,
            user=self.user,
            password=self.password,
        )


@dataclass
class AppConfig:
    log_level: str = "INFO"

    @classmethod
    def from_env(cls) -> AppConfig:
        return cls(
            log_level=os.getenv("LOG_LEVEL", "INFO"),
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
