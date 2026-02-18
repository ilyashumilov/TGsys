from __future__ import annotations

import json
import logging
import signal
import sys
import time
from typing import Any

from config import AppConfig, KafkaConfig, setup_logging
from custom_clients.kafka_client import KafkaConfig as KafkaClientConfig, KafkaConsumerClient


class PostEventProcessor:
    """Processes new post events from Kafka."""

    def __init__(self, consumer: KafkaConsumerClient):
        self._consumer = consumer
        self._logger = logging.getLogger(__name__)

    def process_event(self, event_data: dict[str, Any]) -> None:
        """Process a single post event."""
        channel_id = event_data.get("channel_id", "unknown")
        message_id = event_data.get("message_id", "unknown")
        channel_identifier = event_data.get("channel_identifier", "unknown")
        timestamp = event_data.get("timestamp", "unknown")

        self._logger.info("New post event received:")
        self._logger.info(f"   Channel: {channel_identifier} (ID: {channel_id})")
        self._logger.info(f"   Message ID: {message_id}")
        self._logger.info(f"   Timestamp: {timestamp}")
        self._logger.info("-" * 50)

    def run(self) -> None:
        """Main event processing loop."""
        self._logger.info("Starting Post Commenter Service...")
        self._logger.info(f"Listening for events on topic: {self._consumer._topic}")
        
        try:
            for message in self._consumer:
                try:
                    event_data = json.loads(message.value)
                    self.process_event(event_data)
                except json.JSONDecodeError as e:
                    self._logger.error(f"Failed to parse JSON: {e}")
                    self._logger.error(f"Raw message: {message.value}")
                except Exception as e:
                    self._logger.error(f"Error processing message: {e}", exc_info=True)
        except KeyboardInterrupt:
            self._logger.info("Received interrupt signal, shutting down...")
        except Exception as e:
            self._logger.error(f"Fatal error in consumer loop: {e}", exc_info=True)


def main() -> None:
    """Main entry point for the Post Commenter Service."""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("Starting Post Commenter Service...")
        
        # Load configuration
        app_config = AppConfig.from_env()
        kafka_config = KafkaConfig.from_env()
        
        logger.info(f"Configuration loaded:")
        logger.info(f"   Kafka Broker: {kafka_config.broker}")
        logger.info(f"   Topic: {kafka_config.topic}")
        logger.info(f"   Consumer Group: {kafka_config.consumer_group}")
        logger.info(f"   Start Delay: {kafka_config.start_delay}s")
        
        # Wait for Kafka to be ready
        logger.info(f"Waiting {kafka_config.start_delay}s for Kafka to be ready...")
        time.sleep(kafka_config.start_delay)
        
        # Initialize Kafka consumer
        kafka_client_config = KafkaClientConfig(
            broker=kafka_config.broker,
            topic=kafka_config.topic,
        )
        
        with KafkaConsumerClient(kafka_client_config, group_id=kafka_config.consumer_group) as consumer:
            processor = PostEventProcessor(consumer)
            
            # Setup graceful shutdown
            def shutdown_handler(signum, frame):
                logger.info(f"Received signal {signum}, initiating graceful shutdown...")
                sys.exit(0)
            
            signal.signal(signal.SIGINT, shutdown_handler)
            signal.signal(signal.SIGTERM, shutdown_handler)
            
            logger.info("Service started successfully")
            processor.run()
            
    except Exception as exc:
        logger.error(f"Fatal error in main: {exc}", exc_info=True)
        sys.exit(1)
    finally:
        logger.info("Service stopped")


if __name__ == "__main__":
    main()