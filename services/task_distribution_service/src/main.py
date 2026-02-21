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
from metrics_exporter import init_metrics_exporter, get_metrics_exporter


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
        self._metrics_exporter = get_metrics_exporter()
        
        self._running = False
        self._task_counter = 0
        self._retry_task: asyncio.Task | None = None

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
            self._retry_task = asyncio.create_task(self._retry_pending_tasks())
            await self._process_messages()
            
        except Exception as e:
            self._logger.error(f"Failed to start Task Distribution Service: {e}")
            raise

    async def stop(self) -> None:
        """Stop task distribution service."""
        self._logger.info("Stopping Task Distribution Service...")
        
        self._running = False
        
        # Cancel retry task
        if self._retry_task:
            self._retry_task.cancel()
            try:
                await self._retry_task
            except asyncio.CancelledError:
                pass
        
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
            post_text = message_data.get('text', '')[:100]  # First 100 chars of post text
            post_date = message_data.get('date', 'unknown')
            
            # Generate task ID
            task_id = f"task_{self._task_counter}"
            self._task_counter += 1
            
            # Record task queued but don't increment pending count yet
            if self._metrics_exporter:
                self._metrics_exporter.record_task_queued(task_id)
                # Keep current pending count, don't increment yet
            
            # Log new task received with full details
            self._logger.info(
                f"🔥 NEW TASK RECEIVED: {channel_identifier}\n"
                f"   ├─ Task ID: {task_id}\n"
                f"   ├─ Message ID: {message_id}\n"
                f"   ├─ Channel ID: {channel_id}\n"
                f"   ├─ Post Date: {post_date}\n"
                f"   ├─ Post Preview: {post_text}{'...' if len(post_text) >= 100 else ''}\n"
                f"   └─ Status: Ready for assignment"
            )
            
            # Check available accounts before assignment
            self._logger.info("🔍 Searching for available accounts...")
            available_accounts = []
            account = None
            
            try:
                available_accounts = await self._db.get_available_accounts_list(
                    min_health_score=self._app_config.min_health_score,
                    cooldown_minutes=self._app_config.cooldown_minutes
                )
                
                if available_accounts:
                    self._logger.info(
                        f"📊 Found {len(available_accounts)} available accounts:\n" +
                        "\n".join([
                            f"   ├─ Account {acc['id']}: Health={acc['health_score']}, "
                            f"Comments={acc['comments_count']}, Last Activity={acc['last_activity']}"
                            for acc in available_accounts[:3]  # Show top 3
                        ])
                    )
                else:
                    self._logger.warning("⚠️  No available accounts found in system")
                
                # Update account availability metrics
                if self._metrics_exporter:
                    busy_accounts = max(0, len(available_accounts) - 5)  # Estimate busy accounts
                    avg_health = sum(acc['health_score'] for acc in available_accounts) / len(available_accounts) if available_accounts else 0
                    self._metrics_exporter.update_account_availability(
                        available=len(available_accounts),
                        busy=busy_accounts,
                        avg_health=avg_health
                    )
                
                # Find best available account
                account = await self._db.get_available_account(
                    min_health_score=self._app_config.min_health_score,
                    cooldown_minutes=self._app_config.cooldown_minutes
                )
                
            except Exception as db_error:
                self._logger.error(f"❌ Database error: {db_error}")
                # Update metrics to show database issues
                if self._metrics_exporter:
                    self._metrics_exporter.update_account_availability(
                        available=0,
                        busy=0,
                        avg_health=0
                    )
            
            if account:
                # Log task assignment details
                self._logger.info(
                    f"🎯 TASK ASSIGNED: Account {account['id']}\n"
                    f"   ├─ Account Health: {account['health_score']}\n"
                    f"   ├─ Total Comments: {account['comments_count']}\n"
                    f"   ├─ Last Activity: {account['last_activity']}\n"
                    f"   ├─ Channel: {channel_identifier}\n"
                    f"   ├─ Message ID: {message_id}\n"
                    f"   └─ Status: Publishing to comment queue..."
                )
                
                # Record task assignment
                if self._metrics_exporter:
                    self._metrics_exporter.record_task_assigned(task_id, str(account['id']))
                
                # Assign task to account
                success = await self._producer.publish_comment_task(
                    account_id=account['id'],
                    channel_id=channel_id,
                    message_id=message_id,
                    channel_identifier=channel_identifier
                )
                
                if success:
                    self._logger.info(
                        f"✅ TASK PUBLISHED SUCCESSFULLY\n"
                        f"   ├─ Account {account['id']} will comment on {channel_identifier}\n"
                        f"   ├─ Message ID: {message_id}\n"
                        f"   └─ Ready for worker pickup"
                    )
                    # Record task completion (assignment phase)
                    if self._metrics_exporter:
                        self._metrics_exporter.record_task_completion(str(account['id']), 1.0, success=True)
                        # Decrement pending tasks since task was assigned
                        current_pending = self._metrics_exporter.pending_tasks_gauge._value._value if hasattr(self._metrics_exporter.pending_tasks_gauge, '_value') else 0
                        self._metrics_exporter.update_pending_tasks(max(0, current_pending - 1))
                else:
                    self._logger.error(
                        f"❌ TASK PUBLICATION FAILED\n"
                        f"   ├─ Account {account['id']}\n"
                        f"   ├─ Channel: {channel_identifier}\n"
                        f"   ├─ Message ID: {message_id}\n"
                        f"   └─ Action: Reducing account health score by 5"
                    )
                    # Reduce health score for failed task assignment
                    try:
                        await self._db.update_account_health(account['id'], -5)
                    except:
                        pass  # Ignore health update errors
                    # Record failed task completion
                    if self._metrics_exporter:
                        self._metrics_exporter.record_task_completion(str(account['id']), 1.0, success=False)
                        # Keep pending tasks count since task failed
            else:
                # Log detailed information about no available accounts
                self._logger.warning(
                    f"❌ NO AVAILABLE ACCOUNTS\n"
                    f"   ├─ Channel: {channel_identifier}\n"
                    f"   ├─ Message ID: {message_id}\n"
                    f"   ├─ Required Health Score: >{self._app_config.min_health_score}\n"
                    f"   ├─ Cooldown Period: {self._app_config.cooldown_minutes} minutes\n"
                    f"   └─ Status: Task stored for periodic retry"
                )
                
                # Store task for retry
                try:
                    task_id = await self._db.insert_pending_task(
                        channel_id=channel_id,
                        message_id=message_id,
                        channel_identifier=channel_identifier,
                        post_text=post_text,
                        post_date=post_date
                    )
                    self._logger.info(f" Task stored with ID {task_id} for retry")
                except Exception as db_error:
                    self._logger.error(f" Failed to store pending task: {db_error}")
                
                # Only increment pending tasks when no accounts are available
                if self._metrics_exporter:
                    # Get current pending count and increment by 1
                    current_pending = self._metrics_exporter.pending_tasks_gauge._value._value if hasattr(self._metrics_exporter.pending_tasks_gauge, '_value') else 0
                    self._metrics_exporter.update_pending_tasks(current_pending + 1)
            
            # Always commit the message
            await self._consumer.commit_message(message)
            
        except Exception as e:
            self._logger.error(f"Error handling message: {e}")
            # Update metrics to show error state
            if self._metrics_exporter:
                self._metrics_exporter.update_pending_tasks(1)
            
            
            # Log final status
            if account:
                self._logger.info(
                    f" TASK PROCESSING COMPLETED\n"
                    f"🏁 TASK PROCESSING COMPLETED\n"
                    f"   ├─ Channel: {channel_identifier}\n"
                    f"   ├─ Message ID: {message_id}\n"
                    f"   ├─ Assigned to: Account {account['id']}\n"
                    f"   └─ Next: Worker will process comment task"
                )
            else:
                self._logger.info(
                    f"🏁 TASK PROCESSING COMPLETED\n"
                    f"   ├─ Channel: {channel_identifier}\n"
                    f"   ├─ Message ID: {message_id}\n"
                    f"   ├─ Status: Task stored for retry\n"
                    f"   └─ Next: Background retry will attempt assignment"
                )
            
        except Exception as e:
            self._logger.error(f"Error handling message: {e}")
            raise

    async def _retry_pending_tasks(self) -> None:
        """Periodically retry pending tasks that couldn't be assigned initially."""
        retry_interval = 60  # seconds
        self._logger.info(f"Starting pending tasks retry loop (every {retry_interval}s)")
        
        while self._running:
            try:
                await asyncio.sleep(retry_interval)
                
                # Get pending tasks (oldest first)
                pending_tasks = await self._db.get_pending_tasks(limit=10)
                
                if not pending_tasks:
                    continue
                
                self._logger.info(f"🔄 Retrying {len(pending_tasks)} pending tasks...")
                
                for task in pending_tasks:
                    try:
                        # Check for available account
                        account = await self._db.get_available_account(
                            min_health_score=self._app_config.min_health_score,
                            cooldown_hours=self._app_config.cooldown_hours
                        )
                        
                        if account:
                            # Generate new task ID for this retry attempt
                            task_id = f"retry_{task['id']}_{self._task_counter}"
                            self._task_counter += 1
                            
                            self._logger.info(
                                f"🎯 RETRY ASSIGNMENT: Task {task['id']} -> Account {account['id']}\n"
                                f"   ├─ Channel: {task['channel_identifier']}\n"
                                f"   ├─ Message ID: {task['message_id']}\n"
                                f"   ├─ Retry Count: {task['retry_count']}\n"
                                f"   └─ Publishing to comment queue..."
                            )
                            
                            # Record task assignment
                            if self._metrics_exporter:
                                self._metrics_exporter.record_task_assigned(task_id, str(account['id']))
                            
                            # Assign task to account
                            success = await self._producer.publish_comment_task(
                                account_id=account['id'],
                                channel_id=task['channel_id'],
                                message_id=task['message_id'],
                                channel_identifier=task['channel_identifier']
                            )
                            
                            if success:
                                self._logger.info(
                                    f"✅ RETRY SUCCESSFUL\n"
                                    f"   ├─ Task {task['id']} assigned to Account {account['id']}\n"
                                    f"   ├─ Channel: {task['channel_identifier']}\n"
                                    f"   └─ Removing from pending tasks"
                                )
                                
                                # Remove from pending tasks
                                await self._db.delete_pending_task(task['id'])
                                
                                # Update metrics - decrement pending tasks
                                if self._metrics_exporter:
                                    current_pending = self._metrics_exporter.pending_tasks_gauge._value._value if hasattr(self._metrics_exporter.pending_tasks_gauge, '_value') else 0
                                    self._metrics_exporter.update_pending_tasks(max(0, current_pending - 1))
                                    self._metrics_exporter.record_task_completion(str(account['id']), 1.0, success=True)
                            else:
                                self._logger.error(
                                    f"❌ RETRY PUBLICATION FAILED\n"
                                    f"   ├─ Task {task['id']}\n"
                                    f"   ├─ Account {account['id']}\n"
                                    f"   └─ Keeping in pending tasks"
                                )
                                # Reduce health score for failed task assignment
                                try:
                                    await self._db.update_account_health(account['id'], -5)
                                except:
                                    pass
                                # Increment retry count
                                await self._db.increment_pending_task_retry(task['id'])
                                if self._metrics_exporter:
                                    self._metrics_exporter.record_task_completion(str(account['id']), 1.0, success=False)
                        else:
                            # No account available, increment retry count
                            await self._db.increment_pending_task_retry(task['id'])
                            self._logger.debug(f"No accounts available for pending task {task['id']}, retry count now {task['retry_count'] + 1}")
                            
                    except Exception as task_error:
                        self._logger.error(f"Error retrying task {task['id']}: {task_error}")
                        # Still increment retry count on error
                        try:
                            await self._db.increment_pending_task_retry(task['id'])
                        except:
                            pass
                            
            except Exception as e:
                self._logger.error(f"Error in pending tasks retry loop: {e}")
                # Continue the loop despite errors


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
        # Initialize metrics exporter
        metrics_exporter = init_metrics_exporter(port=8000)
        logger.info("Metrics exporter initialized on port 8000")
        
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
