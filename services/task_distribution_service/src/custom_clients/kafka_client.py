from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import dataclass
from typing import Optional, Dict, Any

from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
from aiokafka.errors import KafkaError


@dataclass
class KafkaConfig:
    broker: str
    topic: str
    consumer_group: str
    consumer_start_delay: int = 20


class KafkaProducerClient:
    def __init__(self, config: KafkaConfig):
        self._config = config
        self._producer: Optional[AIOKafkaProducer] = None
        self._logger = logging.getLogger(__name__)

    async def connect(self) -> None:
        """Connect to Kafka broker."""
        try:
            self._producer = AIOKafkaProducer(
                bootstrap_servers=self._config.broker,
                value_serializer=lambda v: json.dumps(v, ensure_ascii=False).encode('utf-8'),
                key_serializer=lambda k: k.encode('utf-8') if k else None,
                acks='all',  # Wait for all replicas
                linger_ms=10,
            )
            await self._producer.start()
            self._logger.info(f"Connected to Kafka producer at {self._config.broker}")
        except Exception as e:
            self._logger.error(f"Failed to connect to Kafka producer: {e}")
            raise

    async def disconnect(self) -> None:
        """Disconnect from Kafka broker."""
        if self._producer:
            await self._producer.stop()
            self._logger.info("Kafka producer disconnected")

    async def publish_comment_task(
        self, 
        account_id: int, 
        channel_id: int, 
        message_id: int,
        channel_identifier: str
    ) -> bool:
        """Publish comment task to Kafka."""
        if not self._producer:
            raise RuntimeError("Producer not connected")
        
        try:
            task_id = str(uuid.uuid4())
            task_data = {
                "task_id": task_id,
                "account_id": account_id,
                "channel_id": channel_id,
                "message_id": message_id,
                "channel_identifier": channel_identifier,
                "timestamp": int(time.time())
            }
            
            # Send to comment-tasks topic with account_id as key
            await self._producer.send_and_wait(
                topic="comment-tasks",
                key=str(account_id),
                value=task_data
            )
            
            self._logger.info(
                f"Published comment task {task_id} for account {account_id} "
                f"to channel {channel_identifier}"
            )
            return True
            
        except KafkaError as e:
            self._logger.error(f"Failed to publish comment task: {e}")
            return False
        except Exception as e:
            self._logger.error(f"Unexpected error publishing comment task: {e}")
            return False


class KafkaConsumerClient:
    def __init__(self, config: KafkaConfig):
        self._config = config
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
                f"for topic {self._config.topic}"
            )
        except Exception as e:
            self._logger.error(f"Failed to connect to Kafka consumer: {e}")
            raise

    async def disconnect(self) -> None:
        """Disconnect from Kafka broker."""
        if self._consumer:
            await self._consumer.stop()
            self._logger.info("Kafka consumer disconnected")

    async def consume_messages(self):
        """Consume messages from Kafka."""
        if not self._consumer:
            raise RuntimeError("Consumer not connected")
        
        try:
            async for message in self._consumer:
                yield message
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
