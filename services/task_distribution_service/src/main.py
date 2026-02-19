from __future__ import annotations

import asyncio
import logging
import signal
import sys
import time
from typing import Dict, Any

from config import AppConfig, KafkaConfig, PostgresConfig, setup_logging
from custom_clients.kafka_client import KafkaConfig as KafkaClientConfig, KafkaProducerClient, KafkaConsumerClient
from custom_clients.postgres_client import PostgresClient, PostgresConnection


class TaskDistributionService:
    """Service for distributing comment tasks to available accounts."""

    def __init__(
        self,
        app_config: AppConfig,
        kafka_config: KafkaConfig,
        postgres_config: PostgresConfig,
    ):
        self._app_config = app_config
        self._kafka_config = kafka_config
        self._postgres_config = postgres_config
        self._logger = logging.getLogger(__name__)
        
        # Initialize components
        self._db: PostgresClient | None = None
        self._consumer: KafkaConsumerClient | None = None
        self._producer: KafkaProducerClient | None = None
        
        self._running = False

    async def start(self) -> None:
        """Start task distribution service."""
        try:
            self._logger.info("Starting Task Distribution Service...")
            
            # Wait for Kafka to be ready
            self._logger.info(f"Waiting {self._kafka_config.consumer_start_delay}s for Kafka...")
            await asyncio.sleep(self._kafka_config.consumer_start_delay)
            
            # Initialize database connection
            self._db = PostgresClient(PostgresConnection(
                host=self._postgres_config.host,
                port=self._postgres_config.port,
                database=self._postgres_config.db,
                user=self._postgres_config.user,
                password=self._postgres_config.password,
            ))
            await self._db.connect()
            
            # Initialize Kafka clients
            self._consumer = KafkaConsumerClient(KafkaClientConfig(
                broker=self._kafka_config.broker,
                topic=self._kafka_config.topic,
                consumer_group=self._kafka_config.consumer_group,
                consumer_start_delay=self._kafka_config.consumer_start_delay
            ))
            await self._consumer.connect()
            
            self._producer = KafkaProducerClient(KafkaClientConfig(
                broker=self._kafka_config.broker,
                topic="comment-tasks",  # Output topic
                consumer_group=self._kafka_config.consumer_group
            ))
            await self._producer.connect()
            
            # Start processing messages
            self._running = True
            await self._process_messages()
            
        except Exception as e:
            self._logger.error(f"Failed to start Task Distribution Service: {e}")
            raise

    async def stop(self) -> None:
        """Stop task distribution service."""
        self._logger.info("Stopping Task Distribution Service...")
        
        self._running = False
        
        # Close connections
        if self._consumer:
            await self._consumer.disconnect()
        
        if self._producer:
            await self._producer.disconnect()
        
        if self._db:
            await self._db.close()
        
        self._logger.info("Task Distribution Service stopped")

    async def _process_messages(self) -> None:
        """Process incoming messages from Kafka."""
        if not self._consumer or not self._producer or not self._db:
            raise RuntimeError("Service not properly initialized")
        
        self._logger.info("Starting message processing...")
        
        try:
            async for message in self._consumer.consume_messages():
                try:
                    await self._handle_message(message)
                except Exception as e:
                    self._logger.error(f"Error handling message: {e}")
                    # Still commit to avoid reprocessing bad messages
                    await self._consumer.commit_message(message)
                    
        except Exception as e:
            self._logger.error(f"Message processing failed: {e}")
            raise

    async def _handle_message(self, message) -> None:
        """Handle individual message."""
        try:
            # Parse message data
            message_data = message.value
            channel_id = message_data.get('channel_id')
            message_id = message_data.get('message_id')
            channel_identifier = message_data.get('channel_identifier', f'channel_{channel_id}')
            
            self._logger.info(
                f"Processing message from {channel_identifier}: "
                f"message_id={message_id}"
            )
            
            # Find available account
            account = await self._db.get_available_account(
                min_health_score=self._app_config.min_health_score,
                cooldown_hours=self._app_config.cooldown_hours
            )
            
            if account:
                # Assign task to account
                success = await self._producer.publish_comment_task(
                    account_id=account['id'],
                    channel_id=channel_id,
                    message_id=message_id,
                    channel_identifier=channel_identifier
                )
                
                if success:
                    self._logger.info(
                        f"✅ Assigned task to account {account['id']} "
                        f"(comments: {account['comments_count']}, health: {account['health_score']})"
                    )
                else:
                    self._logger.error(f"Failed to publish task for account {account['id']}")
                    # Reduce health score for failed task assignment
                    await self._db.update_account_health(account['id'], -5)
            else:
                # No available accounts
                self._logger.warning(
                    f"❌ No available accounts for {channel_identifier} "
                    f"(min_health: {self._app_config.min_health_score}, "
                    f"cooldown: {self._app_config.cooldown_hours}h)"
                )
            
            # Commit message regardless of task assignment
            await self._consumer.commit_message(message)
            
        except Exception as e:
            self._logger.error(f"Error handling message: {e}")
            raise


async def main() -> None:
    """Main entry point."""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    service = None
    shutdown_event = asyncio.Event()
    
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}")
        shutdown_event.set()
    
    # Setup signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        # Load configuration
        app_config = AppConfig.from_env()
        kafka_config = KafkaConfig.from_env()
        postgres_config = PostgresConfig.from_env()
        
        # Initialize and start service
        service = TaskDistributionService(app_config, kafka_config, postgres_config)
        await service.start()
        
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Service failed: {e}")
        sys.exit(1)
    finally:
        if service:
            await service.stop()


if __name__ == "__main__":
    asyncio.run(main())
