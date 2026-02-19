from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Optional

from aiokafka import AIOKafkaConsumer
from aiokafka.errors import KafkaError


@dataclass
class KafkaConsumerConfig:
    broker: str
    topic: str
    consumer_group: str
    consumer_start_delay: int = 20


class KafkaConsumerClient:
    def __init__(self, config: KafkaConsumerConfig, account_id: int):
        self._config = config
        self._account_id = account_id
        self._consumer: Optional[AIOKafkaConsumer] = None
        self._logger = logging.getLogger(__name__)

    async def connect(self) -> None:
        """Connect to Kafka broker."""
        try:
            self._consumer = AIOKafkaConsumer(
                self._config.topic,
                bootstrap_servers=self._config.broker,
                group_id=self._config.consumer_group,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                key_deserializer=lambda k: k.decode('utf-8') if k else None,
                enable_auto_commit=False,  # Manual acknowledgment
                auto_offset_reset='latest',
                session_timeout_ms=30000,
                heartbeat_interval_ms=3000,
            )
            await self._consumer.start()
            self._logger.info(
                f"Connected to Kafka consumer at {self._config.broker} "
                f"for topic {self._config.topic} (account {self._account_id})"
            )
        except Exception as e:
            self._logger.error(f"Failed to connect to Kafka consumer: {e}")
            raise

    async def disconnect(self) -> None:
        """Disconnect from Kafka broker."""
        if self._consumer:
            await self._consumer.stop()
            self._logger.info("Kafka consumer disconnected")

    async def consume_account_messages(self):
        """Consume messages assigned to this account."""
        if not self._consumer:
            raise RuntimeError("Consumer not connected")
        
        try:
            async for message in self._consumer:
                # Only process messages assigned to this account
                if message.key and str(message.key) == str(self._account_id):
                    yield message
                else:
                    # Commit messages not for this account
                    await self.commit_message(message)
                    
        except Exception as e:
            self._logger.error(f"Error consuming messages: {e}")
            raise

    async def commit_message(self, message) -> None:
        """Manually commit message offset."""
        if not self._consumer:
            raise RuntimeError("Consumer not connected")
        
        try:
            await self._consumer.commit()
            self._logger.debug(f"Committed message offset: {message.offset}")
        except Exception as e:
            self._logger.error(f"Failed to commit message: {e}")
            raise
