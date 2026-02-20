from __future__ import annotations

import os
from dataclasses import dataclass


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
            topic=os.getenv("KAFKA_TOPIC", "comment-tasks"),
            consumer_group=os.getenv("KAFKA_CONSUMER_GROUP", "worker-default"),
            consumer_start_delay=int(os.getenv("KAFKA_CONSUMER_START_DELAY", "20")),
        )


@dataclass
class TelegramConfig:
    api_id: int
    api_hash: str
    session_file: str
    tdata_path: str

    @classmethod
    def from_env(cls) -> "TelegramConfig":
        api_id = int(os.getenv("TELEGRAM_API_ID", "0"))
        api_hash = os.getenv("TELEGRAM_API_HASH", "dummy")
        session_file = os.getenv("SESSION_FILE", "/app/sessions/default_session.session")
        tdata_path = os.getenv("TELEGRAM_TDATA_PATH", "/app/sessions/tdata/default/tdata")

        return cls(api_id=api_id, api_hash=api_hash, session_file=session_file, tdata_path=tdata_path)


@dataclass
class AppConfig:
    account_id: int
    log_level: str = "INFO"
    max_retries: int = 3
    retry_delay: int = 5
    health_check_interval: int = 60

    @classmethod
    def from_env(cls) -> AppConfig:
        return cls(
            account_id=int(os.getenv("ACCOUNT_ID")),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            max_retries=int(os.getenv("MAX_RETRIES", "3")),
            retry_delay=int(os.getenv("RETRY_DELAY", "5")),
            health_check_interval=int(os.getenv("HEALTH_CHECK_INTERVAL", "60")),
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
