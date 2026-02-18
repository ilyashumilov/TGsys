from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Callable, Iterable

from kafka import KafkaConsumer, KafkaProducer


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
    Thin OO wrapper around kafka-python producer.

    Responsible only for connecting to Kafka and sending messages.
    Business logic that decides *what* to send lives elsewhere.
    """

    def __init__(self, config: KafkaConfig):
        self._config = config
        self._producer = KafkaProducer(
            bootstrap_servers=[config.broker],
            key_serializer=lambda k: k.encode("utf-8") if k is not None else None,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        )

    @property
    def topic(self) -> str:
        return self._config.topic

    def send_json(self, key: str, payload: dict[str, Any]) -> None:
        """
        Send a JSON-serialisable payload to the configured topic.
        """
        self._producer.send(self._config.topic, key=key, value=payload)
        self._producer.flush()

    def close(self) -> None:
        self._producer.flush()
        self._producer.close()

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

