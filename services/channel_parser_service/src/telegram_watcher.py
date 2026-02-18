from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any

from telethon import utils
from telethon.sync import TelegramClient

from channel_repository import ChannelRepository, TrackedChannel
from config import TelegramConfig
from kafka.client import KafkaProducerClient


class TelegramSessionManager:
    """
    Ensures the service uses a pre-authorized Telethon session file.
    """

    def __init__(self, session_path: str):
        self._session_path = session_path

    def telethon_session_name(self) -> str:
        # Telethon appends ".session" for string session names, so strip it if provided.
        return self._session_path[:-8] if self._session_path.endswith(".session") else self._session_path

    def assert_session_exists(self) -> None:
        expected_file = (
            self._session_path if self._session_path.endswith(".session") else f"{self._session_path}.session"
        )
        if not os.path.exists(expected_file):
            raise RuntimeError(
                f"Telegram session file not found at {expected_file!r}. "
                f"Mount your authorized session file into the container and set TELEGRAM_SESSION_PATH."
            )


@dataclass(frozen=True)
class LastPostEvent:
    tg_channel_id: int
    message_id: int

    def to_payload(self) -> dict[str, Any]:
        return {"channel_id": self.tg_channel_id, "message_id": self.message_id}


class TelegramChannelWatcher:
    """
    Watches Telegram channels listed in Postgres and publishes last post info to Kafka.
    """

    def __init__(
        self,
        tg_config: TelegramConfig,
        repo: ChannelRepository,
        producer: KafkaProducerClient,
        tick_seconds: float = 3.0,
    ):
        self._tg_config = tg_config
        self._repo = repo
        self._producer = producer
        self._tick_seconds = tick_seconds
        self._session = TelegramSessionManager(tg_config.session_path)

        self._channel_id_by_peer: dict[int, int] = {}
        self._entity_by_channel_row_id: dict[int, object] = {}

    def _publish(self, event: LastPostEvent) -> None:
        key = str(event.tg_channel_id)
        self._producer.send_json(key=key, payload=event.to_payload())

    def _resolve_channel(self, client: TelegramClient, ch: TrackedChannel) -> tuple[int, object]:
        """
        Resolve DB channel identifier to a Telethon entity + stable peer id.
        """
        if ch.id in self._entity_by_channel_row_id:
            entity = self._entity_by_channel_row_id[ch.id]
        else:
            entity = client.get_entity(ch.identifier)
            self._entity_by_channel_row_id[ch.id] = entity

        peer_id = int(utils.get_peer_id(entity))

        if ch.tg_channel_id != peer_id:
            self._repo.update_peer_id(channel_id=ch.id, tg_channel_id=peer_id)

        self._channel_id_by_peer[peer_id] = ch.id
        return peer_id, entity

    def _tick_once(self, client: TelegramClient) -> None:
        channels = self._repo.list_active()
        for ch in channels:
            try:
                peer_id, entity = self._resolve_channel(client, ch)
                last_msg = client.get_messages(entity, limit=1)
                if not last_msg:
                    continue

                latest_message_id = int(last_msg[0].id)
                if latest_message_id > ch.last_message_id:
                    self._publish(LastPostEvent(tg_channel_id=peer_id, message_id=latest_message_id))
                    self._repo.set_last_message_id(channel_id=ch.id, last_message_id=latest_message_id)
            except Exception as exc:
                print(f"[telegram] tick error for {ch.identifier!r}: {exc}")

    def run(self) -> None:
        self._session.assert_session_exists()

        session_name = self._session.telethon_session_name()
        print("[telegram] starting client...")

        with TelegramClient(session_name, self._tg_config.api_id, self._tg_config.api_hash) as client:
            if not client.is_user_authorized():
                raise RuntimeError(
                    "Telegram client is not authorized. Provide a valid authorized session file."
                )

            print("[telegram] polling for last posts...")
            self._tick_once(client)
            while True:
                self._tick_once(client)
                time.sleep(self._tick_seconds)

