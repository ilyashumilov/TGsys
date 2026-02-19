from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass
from typing import Any, Callable, Iterable

from kafka import KafkaConsumer, KafkaProducer
from kafka.errors import KafkaError, KafkaTimeoutError


@dataclass
class KafkaConfig:
    broker: str
    topic: str

    @classmethod
    def from_env(cls) -> "KafkaConfig":
        """
        Read basic Kafka settings from environment variables.

        - KAFKA_BROKER: e.g. "kafka:9092" (default "localhost:9092")
        - KAFKA_TOPIC: name of topic to publish / consume (default "test-topic")
        """
        broker = os.getenv("KAFKA_BROKER", "localhost:9092")
        topic = os.getenv("KAFKA_TOPIC", "test-topic")
        return cls(broker=broker, topic=topic)


class KafkaProducerClient:
    """
    Enhanced Kafka producer with retry logic and error handling.
    
    Responsible only for connecting to Kafka and sending messages.
    Business logic that decides *what* to send lives elsewhere.
    """

    def __init__(self, config: KafkaConfig, max_retries: int = 3, retry_delay: float = 1.0):
        self._config = config
        self._max_retries = max_retries
        self._retry_delay = retry_delay
        self._logger = logging.getLogger(__name__)
        self._producer = None
        self._connect()

    def _connect(self) -> None:
        """Establish connection to Kafka with retry logic."""
        for attempt in range(self._max_retries):
            try:
                self._producer = KafkaProducer(
                    bootstrap_servers=[self._config.broker],
                    key_serializer=lambda k: k.encode("utf-8") if k is not None else None,
                    value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                    request_timeout_ms=30000,
                    retries=self._max_retries,
                    acks='all',  # Wait for all replicas
                )
                self._logger.info(f"Connected to Kafka broker: {self._config.broker}")
                return
            except (KafkaError, KafkaTimeoutError) as e:
                self._logger.warning(f"Kafka connection attempt {attempt + 1} failed: {e}")
                if attempt < self._max_retries - 1:
                    time.sleep(self._retry_delay * (2 ** attempt))  # Exponential backoff
                else:
                    raise KafkaError(f"Failed to connect to Kafka after {self._max_retries} attempts: {e}")

    @property
    def topic(self) -> str:
        return self._config.topic

    def send_json(self, key: str, payload: dict[str, Any]) -> None:
        """
        Send a JSON-serialisable payload to the configured topic with retry logic.
        """
        for attempt in range(self._max_retries):
            try:
                future = self._producer.send(self._config.topic, key=key, value=payload)
                record_metadata = future.get(timeout=10)  # Wait for acknowledgment
                self._logger.debug(
                    f"Message sent to topic {record_metadata.topic} "
                    f"partition {record_metadata.partition} offset {record_metadata.offset}"
                )
                return
            except (KafkaError, KafkaTimeoutError) as e:
                self._logger.warning(f"Kafka send attempt {attempt + 1} failed: {e}")
                if attempt < self._max_retries - 1:
                    time.sleep(self._retry_delay)
                else:
                    raise KafkaError(f"Failed to send message after {self._max_retries} attempts: {e}")

    def flush(self, timeout: float = 10.0) -> None:
        """Flush pending messages."""
        try:
            self._producer.flush(timeout=timeout)
        except KafkaError as e:
            self._logger.error(f"Kafka flush failed: {e}")

    def close(self) -> None:
        """Close the producer connection."""
        if self._producer:
            try:
                self.flush()
                self._producer.close()
                self._logger.info("Kafka producer closed")
            except KafkaError as e:
                self._logger.error(f"Error closing Kafka producer: {e}")

    def __enter__(self) -> "KafkaProducerClient":
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()


class KafkaConsumerClient:
    """
    Thin OO wrapper around kafka-python consumer.

    Exposes a simple loop with a callback for each message.
    """

    def __init__(
        self,
        config: KafkaConfig,
        group_id: str | None = None,
        auto_offset_reset: str = "earliest",
    ):
        self._config = config
        self._consumer = KafkaConsumer(
            config.topic,
            bootstrap_servers=[config.broker],
            group_id=group_id,
            auto_offset_reset=auto_offset_reset,
            enable_auto_commit=True,
            value_deserializer=lambda v: v.decode("utf-8") if v is not None else "",
        )

    @property
    def topic(self) -> str:
        return self._config.topic

    def __iter__(self) -> Iterable:
        return iter(self._consumer)

    def consume_forever(self, handler: Callable[[str, str], None]) -> None:
        """
        Call `handler(topic, value)` for every message in the stream.
        """
        for message in self._consumer:
            handler(message.topic, message.value)

    def close(self) -> None:
        self._consumer.close()

    def __enter__(self) -> "KafkaConsumerClient":
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

