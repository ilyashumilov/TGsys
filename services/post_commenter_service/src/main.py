from __future__ import annotations

import asyncio
import json
import logging
import os
import signal
import sys
import time
from typing import Any

from config import AppConfig, KafkaConfig, PostgresConfig, WorkerConfig, setup_logging
from custom_clients.kafka_client import KafkaConfig as KafkaClientConfig, KafkaConsumerClient
from custom_clients.postgres_client import PostgresClient, PostgresConnection
from account_repository import AccountRepository
from session_manager import SessionManager
from worker_pool import WorkerPool
from comment_generator import CommentGenerator
from task_processor import TaskProcessor


class PostCommenterService:
    """Main service for processing Telegram post events and posting comments."""

    def __init__(
        self,
        kafka_config: KafkaConfig,
        postgres_config: PostgresConfig,
        worker_config: WorkerConfig,
    ):
        self._kafka_config = kafka_config
        self._postgres_config = postgres_config
        self._worker_config = worker_config
        self._logger = logging.getLogger(__name__)
        
        # Initialize components
        self._db: PostgresClient | None = None
        self._account_repo: AccountRepository | None = None
        self._session_manager: SessionManager | None = None
        self._worker_pool: WorkerPool | None = None
        self._comment_generator: CommentGenerator | None = None
        self._task_processor: TaskProcessor | None = None
        self._consumer: KafkaConsumerClient | None = None

    async def start(self) -> None:
        """Start post commenter service."""
        try:
            self._logger.info("Starting Post Commenter Service...")
            
            # Initialize database connection
            await self._init_database()
            
            # Initialize session manager
            await self._init_session_manager()
            
            # Initialize worker pool
            await self._init_worker_pool()
            
            # Initialize comment generator
            self._comment_generator = CommentGenerator()
            
            # Initialize task processor
            self._task_processor = TaskProcessor(
                self._session_manager,
                self._worker_pool,
                self._comment_generator,
            )
            
            # Initialize Kafka consumer
            await self._init_kafka_consumer()
            
            # Start processing events
            await self._run_event_loop()
            
        except Exception as e:
            self._logger.error(f"Error starting service: {e}", exc_info=True)
            raise

    async def _init_database(self) -> None:
        """Initialize database connection and repository."""
        self._db = PostgresClient(
            PostgresConnection(
                host=self._postgres_config.host,
                port=self._postgres_config.port,
                db=self._postgres_config.db,
                user=self._postgres_config.user,
                password=self._postgres_config.password,
            )
        )
        self._account_repo = AccountRepository(self._db)
        self._logger.info("Database connection initialized")

    async def _init_session_manager(self) -> None:
        """Initialize session manager."""
        tracker_api_id = int(os.getenv("TRACKER_API_ID", "0"))
        self._session_manager = SessionManager(self._worker_config.sessions_dir, tracker_api_id)
        
        # Sync accounts with database
        self._session_manager.sync_accounts_with_database(self._account_repo)
        self._logger.info("Session manager initialized")

    async def _init_worker_pool(self) -> None:
        """Initialize worker pool."""
        self._worker_pool = WorkerPool(
            self._account_repo,
            self._worker_config.min_cooldown_minutes,
            self._worker_config.max_cooldown_minutes,
        )
        
        # Log pool status
        status = self._worker_pool.get_pool_status()
        self._logger.info(f"Worker pool initialized: {status}")

    async def _init_kafka_consumer(self) -> None:
        """Initialize Kafka consumer with manual acknowledgment."""
        kafka_client_config = KafkaClientConfig(
            broker=self._kafka_config.broker,
            topic=self._kafka_config.topic,
        )
        
        self._consumer = KafkaConsumerClient(
            kafka_client_config,
            group_id=self._kafka_config.consumer_group,
            auto_offset_reset="earliest",
            enable_auto_commit=False,  # Manual acknowledgment
        )
        
        self._logger.info("Kafka consumer initialized")

    async def _run_event_loop(self) -> None:
        """Run the main event processing loop."""
        self._logger.info("Starting event processing loop...")
        
        try:
            async for message in self._consumer:
                try:
                    # Parse event data
                    event_data = json.loads(message.value)
                    
                    # Process event
                    success = await self._task_processor.process_event(event_data)
                    
                    if success:
                        # Acknowledge message only after successful processing
                        await self._consumer.commit()
                        self._logger.info("Event processed and acknowledged")
                    else:
                        self._logger.error("Failed to process event, message will be retried")
                        
                except json.JSONDecodeError as e:
                    self._logger.error(f"Failed to parse JSON: {e}")
                    self._logger.error(f"Raw message: {message.value}")
                    # Still acknowledge to avoid poison pills
                    await self._consumer.commit()
                except Exception as e:
                    self._logger.error(f"Error processing message: {e}", exc_info=True)
                    # Don't acknowledge on processing error, allow retry
                        
        except Exception as e:
            self._logger.error(f"Fatal error in event loop: {e}", exc_info=True)
            raise

    async def stop(self) -> None:
        """Stop the service gracefully."""
        self._logger.info("Stopping Post Commenter Service...")
        
        if self._consumer:
            self._consumer.close()
        
        # PostgresClient doesn't have a close method, just set to None
        self._db = None
        
        self._logger.info("Service stopped")


async def main() -> None:
    """Main entry point for Post Commenter Service."""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    service: PostCommenterService | None = None
    
    try:
        logger.info("Initializing Post Commenter Service...")
        
        # Load configuration
        app_config = AppConfig.from_env()
        kafka_config = KafkaConfig.from_env()
        postgres_config = PostgresConfig.from_env()
        worker_config = WorkerConfig.from_env()
        
        logger.info(f"Configuration loaded:")
        logger.info(f"   Kafka Broker: {kafka_config.broker}")
        logger.info(f"   Topic: {kafka_config.topic}")
        logger.info(f"   Consumer Group: {kafka_config.consumer_group}")
        logger.info(f"   Sessions Dir: {worker_config.sessions_dir}")
        logger.info(f"   Cooldown: {worker_config.min_cooldown_minutes}-{worker_config.max_cooldown_minutes} minutes")
        
        # Wait for dependencies
        logger.info(f"Waiting {kafka_config.start_delay}s for dependencies...")
        await asyncio.sleep(kafka_config.start_delay)
        
        # Create and start service
        service = PostCommenterService(kafka_config, postgres_config, worker_config)
        
        # Setup graceful shutdown
        def shutdown_handler(signum, frame):
            logger.info(f"Received signal {signum}, initiating graceful shutdown...")
            if service:
                asyncio.create_task(service.stop())
            sys.exit(0)
        
        signal.signal(signal.SIGINT, shutdown_handler)
        signal.signal(signal.SIGTERM, shutdown_handler)
        
        logger.info("Service starting...")
        await service.start()
        
    except Exception as exc:
        logger.error(f"Fatal error in main: {exc}", exc_info=True)
        sys.exit(1)
    finally:
        if service:
            await service.stop()
        logger.info("Service stopped")


if __name__ == "__main__":
    asyncio.run(main())