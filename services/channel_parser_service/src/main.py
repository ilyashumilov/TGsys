from __future__ import annotations

import logging
import os
import signal
import sys
from contextlib import ExitStack

from channel_repository import ChannelRepository
from config import AppConfig, PostgresConfig, TelegramConfig
from custom_clients.kafka_client import KafkaConfig, KafkaProducerClient
from custom_clients.postgres_client import PostgresClient, PostgresConnection
from telegram_watcher import TelegramChannelWatcher


def setup_logging() -> None:
    """Configure logging for the application."""
    log_level = os.getenv("LOG_LEVEL", "INFO")
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
        ]
    )


def main() -> None:
    """Main entry point for the Telegram channel parser service."""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("Starting Telegram Channel Parser Service...")
        
        # Load configuration
        app_config = AppConfig.from_env()
        pg_config = PostgresConfig.from_env()
        tg_config = TelegramConfig.from_env()
        kafka_config = KafkaConfig.from_env()
        
        logger.info(f"Configuration loaded - Tick interval: {app_config.tick_seconds}s")
        logger.info(f"PostgreSQL: {pg_config.host}:{pg_config.port}/{pg_config.db}")
        logger.info(f"Kafka: {kafka_config.broker} - Topic: {kafka_config.topic}")
        logger.info(f"Telegram Session Path: {tg_config.session_path}")
        
        # Initialize database connection
        db = PostgresClient(
            PostgresConnection(
                host=pg_config.host,
                port=pg_config.port,
                db=pg_config.db,
                user=pg_config.user,
                password=pg_config.password,
            )
        )
        
        repo = ChannelRepository(db)
        
        # Test database connection
        channels = repo.list_active()
        logger.info(f"Found {len(channels)} active channels to track")
        
        # Add sample channels if table is empty
        if len(channels) == 0:
            logger.info("No channels found, adding sample channels...")
            sample_channels = ['@durov', '@telegram']
            for channel_id in sample_channels:
                try:
                    db.execute(
                        "INSERT INTO telegram_channels (identifier) VALUES (%s) ON CONFLICT (identifier) DO NOTHING",
                        (channel_id,)
                    )
                    logger.info(f"Added sample channel: {channel_id}")
                except Exception as e:
                    logger.warning(f"Could not add channel {channel_id}: {e}")
            
            # Refresh channel list
            channels = repo.list_active()
            logger.info(f"Now tracking {len(channels)} channels")
        
        # Initialize and run the watcher
        with ExitStack() as stack:
            producer = stack.enter_context(KafkaProducerClient(kafka_config))
            watcher = TelegramChannelWatcher(
                tg_config=tg_config,
                repo=repo,
                producer=producer,
                tick_seconds=app_config.tick_seconds,
            )
            
            # Setup graceful shutdown
            def shutdown_handler(signum, frame):
                logger.info(f"Received signal {signum}, initiating graceful shutdown...")
                # The watcher handles KeyboardInterrupt in its run() method
                sys.exit(0)
            
            signal.signal(signal.SIGINT, shutdown_handler)
            signal.signal(signal.SIGTERM, shutdown_handler)
            
            logger.info("Service started successfully")
            watcher.run()
            
    except Exception as exc:
        logger.error(f"Fatal error in main: {exc}", exc_info=True)
        sys.exit(1)
    finally:
        logger.info("Service stopped")


if __name__ == "__main__":
    main()