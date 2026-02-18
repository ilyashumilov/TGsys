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
        start_delay = int(os.getenv("KAFKA_CONSUMER_START_DELAY", "20"))

        return cls(
            broker=broker,
            topic=topic,
            consumer_group=consumer_group,
            start_delay=start_delay,
        )


@dataclass(frozen=True)
class AppConfig:
    log_level: str

    @classmethod
    def from_env(cls) -> "AppConfig":
        log_level = os.getenv("LOG_LEVEL", "INFO")
        return cls(log_level=log_level)
