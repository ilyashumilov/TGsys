from __future__ import annotations

from channel_repository import ChannelRepository
from config import AppConfig, PostgresConfig, TelegramConfig
from kafka.client import KafkaConfig, KafkaProducerClient
from postgres.client import PostgresClient, PostgresConnection
from telegram_watcher import TelegramChannelWatcher


def main() -> None:
    app_config = AppConfig.from_env()
    pg_config = PostgresConfig.from_env()
    tg_config = TelegramConfig.from_env()
    kafka_config = KafkaConfig.from_env()

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

    with KafkaProducerClient(kafka_config) as producer:
        watcher = TelegramChannelWatcher(
            tg_config=tg_config,
            repo=repo,
            producer=producer,
            tick_seconds=app_config.tick_seconds,
        )
        watcher.run()


if __name__ == "__main__":
    main()