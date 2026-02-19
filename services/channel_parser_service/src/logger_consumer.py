from __future__ import annotations

import json
import os
import time
from typing import Any

from custom_clients.kafka_client import KafkaConfig, KafkaConsumerClient


class LoggingConsumerApp:
    """
    Simple application layer that prints every consumed message.
    """

    def __init__(self, consumer: KafkaConsumerClient):
        self._consumer = consumer

    @staticmethod
    def _format_value(raw_value: str) -> str:
        try:
            parsed: Any = json.loads(raw_value)
            return json.dumps(parsed, ensure_ascii=False)
        except Exception:
            return raw_value

    def run(self) -> None:
        for message in self._consumer:
            topic = message.topic
            raw_value = message.value
            
            print(f"{topic};{raw_value}")


def main() -> None:
    # Small startup delay to let Kafka come up
    time.sleep(int(os.getenv("KAFKA_CONSUMER_START_DELAY", "10")))

    config = KafkaConfig.from_env()
    with KafkaConsumerClient(config=config, group_id="logging-consumer") as consumer_client:
        print(f"Starting consumer on broker={config.broker}, topic={config.topic}")
        app = LoggingConsumerApp(consumer_client)
        app.run()


if __name__ == "__main__":
    main()

