from __future__ import annotations

import asyncio
import logging
import signal
import sys
import time
from typing import Dict, Any

from config import AppConfig, KafkaConfig, TelegramConfig, setup_logging
from custom_clients.kafka_client import KafkaConsumerClient, KafkaConsumerConfig
from comment_generator import CommentGenerator
from telegram_client import TelegramCommentClient


class CommentWorkerService:
    """Service for executing comment tasks assigned to a specific account."""

    def __init__(
        self,
        app_config: AppConfig,
        kafka_config: KafkaConfig,
        telegram_config: TelegramConfig,
    ):
        self._app_config = app_config
        self._kafka_config = kafka_config
        self._telegram_config = telegram_config
        self._logger = logging.getLogger(__name__)
        
        # Initialize components
        self._consumer: KafkaConsumerClient | None = None
        self._telegram_client: TelegramCommentClient | None = None
        self._comment_generator: CommentGenerator | None = None
        
        self._running = False

    async def start(self) -> None:
        """Start comment worker service."""
        try:
            self._logger.info(f"Starting Comment Worker Service for account {self._app_config.account_id}...")
            
            # Wait for services to be ready
            self._logger.info(f"Waiting {self._kafka_config.consumer_start_delay}s for services...")
            await asyncio.sleep(self._kafka_config.consumer_start_delay)
            
            # Initialize Kafka consumer
            self._consumer = KafkaConsumerClient(
                KafkaConsumerConfig(
                    broker=self._kafka_config.broker,
                    topic=self._kafka_config.topic,
                    consumer_group=self._kafka_config.consumer_group,
                    consumer_start_delay=self._kafka_config.consumer_start_delay
                ),
                account_id=self._app_config.account_id
            )
            await self._consumer.connect()
            
            self._telegram_client = TelegramCommentClient(
                self._telegram_config.api_id,
                self._telegram_config.api_hash,
                self._telegram_config.session_file,
                tdata_path=self._telegram_config.tdata_path
            )
            
            if not await self._telegram_client.connect():
                raise RuntimeError("Failed to connect to Telegram")
            
            # # Test connection
            # if not await self._telegram_client.test_connection():
            #     raise RuntimeError("Telegram connection test failed")
            
            # Initialize comment generator
            self._comment_generator = CommentGenerator()
            
            # Start processing tasks
            self._running = True
            await self._process_tasks()
            
        except Exception as e:
            self._logger.error(f"Failed to start Comment Worker Service: {e}")
            raise

    async def stop(self) -> None:
        """Stop comment worker service."""
        self._logger.info("Stopping Comment Worker Service...")
        
        self._running = False
        
        # Close connections
        if self._consumer:
            await self._consumer.disconnect()
        
        if self._telegram_client:
            await self._telegram_client.disconnect()
        
        self._logger.info("Comment Worker Service stopped")

    async def _process_tasks(self) -> None:
        """Process assigned comment tasks."""
        if not all([self._consumer, self._telegram_client, self._comment_generator]):
            raise RuntimeError("Service not properly initialized")
        
        self._logger.info("Starting task processing...")
        
        try:
            async for message in self._consumer.consume_account_messages():
                try:
                    await self._handle_task(message)
                except Exception as e:
                    self._logger.error(f"Error handling task: {e}")
                    # Don't commit on error to allow retry
                    
        except Exception as e:
            self._logger.error(f"Task processing failed: {e}")
            raise

    async def _handle_task(self, message) -> None:
        """Handle individual comment task."""
        try:
            # Parse task data
            task_data = message.value
            task_id = task_data.get('task_id')
            channel_id = task_data.get('channel_id')
            message_id = task_data.get('message_id')
            channel_identifier = task_data.get('channel_identifier')
            
            self._logger.info(
                f"Processing task {task_id}: {channel_identifier}:{message_id}"
            )
            
            # Generate comment
            comment_text = self._comment_generator.generate_comment()
            
            # Post comment
            success = await self._telegram_client.post_comment(
                channel_username=channel_identifier,
                message_id=message_id,
                comment_text=comment_text
            )
            
            if success:
                self._logger.info(
                    f"✅ Task {task_id} completed successfully"
                )
                
                # Commit message
                await self._consumer.commit_message(message)
            else:
                self._logger.error(
                    f"❌ Task {task_id} failed - not committing for retry"
                )
                
        except Exception as e:
            self._logger.error(f"Error handling task {task_id}: {e}")
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
        telegram_config = TelegramConfig.from_env()
        
        # Validate required configuration
        if not telegram_config.session_file:
            raise ValueError("SESSION_FILE is required")
        
        # Initialize and start service
        service = CommentWorkerService(
            app_config, kafka_config, telegram_config
        )
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
