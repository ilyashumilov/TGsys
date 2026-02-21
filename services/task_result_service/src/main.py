from __future__ import annotations

import asyncio
import logging
import signal
import sys
from typing import Dict, Any

from config import AppConfig, KafkaConfig, PostgresConfig, setup_logging
from custom_clients.postgres_client import PostgresResultClient
from custom_clients.kafka_client import KafkaResultClient


class TaskResultService:
    """Service for processing task results and updating database."""

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
        self._kafka_client: KafkaResultClient | None = None
        self._postgres_client: PostgresClient | None = None
        
        self._running = False

    async def start(self) -> None:
        """Start task result service."""
        try:
            self._logger.info("Starting Task Result Service...")
            
            # Wait for services to be ready
            self._logger.info(f"Waiting {self._kafka_config.consumer_start_delay}s for services...")
            await asyncio.sleep(self._kafka_config.consumer_start_delay)
            
            # Initialize Postgres client
            self._postgres_client = PostgresResultClient(self._postgres_config.to_connection())
            
            # Initialize Kafka client
            self._kafka_client = KafkaResultClient(
                broker=self._kafka_config.broker,
                result_topic=self._kafka_config.result_topic,
                task_topic=self._kafka_config.task_topic,
                consumer_group=self._kafka_config.consumer_group
            )
            await self._kafka_client.connect()
            
            # Start processing results
            self._running = True
            await self._process_results()
            
        except Exception as e:
            self._logger.error(f"Failed to start Task Result Service: {e}")
            raise

    async def stop(self) -> None:
        """Stop task result service."""
        self._logger.info("Stopping Task Result Service...")
        
        self._running = False
        
        # Close connections
        if self._kafka_client:
            await self._kafka_client.disconnect()
        
        self._logger.info("Task Result Service stopped")

    async def _process_results(self) -> None:
        """Process task results."""
        if not all([self._kafka_client, self._postgres_client]):
            raise RuntimeError("Service not properly initialized")
        
        self._logger.info("Starting result processing...")
        
        try:
            async for message in self._kafka_client.consume_results():
                try:
                    await self._handle_result(message)
                except Exception as e:
                    self._logger.error(f"Error handling result: {e}")
                    # Continue processing other results
                    
        except Exception as e:
            self._logger.error(f"Result processing failed: {e}")
            raise

    async def _handle_result(self, message) -> None:
        """Handle individual task result."""
        try:
            # Parse result data
            result_data = message.value
            task_id = result_data.get('task_id')
            account_id = result_data.get('account_id')
            success = result_data.get('success')
            
            self._logger.info(f"Processing result for task {task_id}, success: {success}")
            
            if success:
                # Update database
                await self._update_account_stats(account_id)
                self._logger.info(f"✅ Updated stats for account {account_id}")
            else:
                # Resend task to worker
                await self._resend_task(result_data)
                self._logger.info(f"🔄 Resent task {task_id} to worker")
            
            # Commit result message
            await self._kafka_client.commit_message(message)
            
        except Exception as e:
            self._logger.error(f"Error handling result for task {task_id}: {e}")
            raise

    async def _update_account_stats(self, account_id: int) -> None:
        """Update account comments_count and last_comment_time."""
        sql = """
        UPDATE telegram_accounts 
        SET comments_count = comments_count + 1, last_comment_time = NOW()
        WHERE id = %s
        """
        self._postgres_client.execute(sql, (account_id,))

    async def _resend_task(self, task_data: dict) -> None:
        """Resend failed task to worker topic."""
        # Remove result-specific fields and resend
        resend_data = {k: v for k, v in task_data.items() if k not in ['success', 'timestamp']}
        await self._kafka_client.send_task(resend_data)


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
        service = TaskResultService(
            app_config, kafka_config, postgres_config
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
