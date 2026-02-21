from __future__ import annotations

import json
import logging
from typing import Optional

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from aiokafka.errors import KafkaError


class KafkaResultClient:
    """Kafka client for consuming task results and resending tasks."""

    def __init__(self, broker: str, result_topic: str, task_topic: str, consumer_group: str):
        self._broker = broker
        self._result_topic = result_topic
        self._task_topic = task_topic
        self._consumer_group = consumer_group
        self._consumer: Optional[AIOKafkaConsumer] = None
        self._producer: Optional[AIOKafkaProducer] = None
        self._logger = logging.getLogger(__name__)

    async def connect(self) -> None:
        """Connect to Kafka broker."""
        try:
            # Initialize consumer
            self._consumer = AIOKafkaConsumer(
                self._result_topic,
                bootstrap_servers=self._broker,
                group_id=self._consumer_group,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                key_deserializer=lambda k: k.decode('utf-8') if k else None,
                enable_auto_commit=False,  # Manual acknowledgment
                auto_offset_reset='latest',
                session_timeout_ms=30000,
                heartbeat_interval_ms=3000,
            )
            await self._consumer.start()
            self._logger.info(
                f"Connected to Kafka consumer at {self._broker} for topic {self._result_topic}"
            )
            
            # Initialize producer
            self._producer = AIOKafkaProducer(
                bootstrap_servers=self._broker,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                key_serializer=lambda k: str(k).encode('utf-8') if k else None,
            )
            await self._producer.start()
            self._logger.info(f"Connected to Kafka producer at {self._broker}")
        except Exception as e:
            self._logger.error(f"Failed to connect to Kafka: {e}")
            raise

    async def disconnect(self) -> None:
        """Disconnect from Kafka broker."""
        if self._consumer:
            await self._consumer.stop()
            self._logger.info("Kafka consumer disconnected")
        
        if self._producer:
            await self._producer.stop()
            self._logger.info("Kafka producer disconnected")

    async def consume_results(self):
        """Consume result messages."""
        if not self._consumer:
            raise RuntimeError("Consumer not connected")
        
        try:
            async for message in self._consumer:
                yield message
        except Exception as e:
            self._logger.error(f"Error consuming results: {e}")
            raise

    async def commit_message(self, message) -> None:
        """Manually commit message offset."""
        if not self._consumer:
            raise RuntimeError("Consumer not connected")
        
        try:
            await self._consumer.commit()
            self._logger.debug(f"Committed result message offset: {message.offset}")
        except Exception as e:
            self._logger.error(f"Failed to commit result message: {e}")
            raise

    async def send_task(self, task_data: dict) -> None:
        """Send task to worker topic."""
        if not self._producer:
            raise RuntimeError("Producer not connected")
        
        try:
            account_id = task_data.get('account_id')
            await self._producer.send_and_wait(
                self._task_topic,
                value=task_data,
                key=account_id
            )
            self._logger.debug(f"Resent task to topic {self._task_topic}: {task_data}")
        except Exception as e:
            self._logger.error(f"Failed to resend task: {e}")
            raise
