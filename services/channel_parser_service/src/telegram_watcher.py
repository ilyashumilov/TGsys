from __future__ import annotations

import asyncio
import logging
import os
import shutil
import sys
import time
from dataclasses import dataclass
from typing import Any

from telethon import utils
from telethon.sync import TelegramClient
from telethon.errors import ChannelPrivateError, ChatAdminRequiredError, FloodWaitError

from channel_repository import ChannelRepository, TrackedChannel
from config import TelegramConfig
from custom_clients.kafka_client import KafkaConfig, KafkaProducerClient

from shared.telegram_session_loader import TDataSessionLoader


class TelegramSessionManager:
    """
    Ensures the service uses a pre-authorized Telethon session file.
    """

    def __init__(self, session_path: str, tdata_path: str = None):
        self._session_path = session_path
        self._tdata_path = tdata_path

    def telethon_session_name(self) -> str:
        # Telethon appends ".session" for string session names, so strip it if provided.
        return self._session_path[:-8] if self._session_path.endswith(".session") else self._session_path

    def prepare_writable_session_name(self, runtime_dir: str = "/tmp") -> str:
        expected_file = (
            self._session_path if self._session_path.endswith(".session") else f"{self._session_path}.session"
        )
        self.assert_session_exists()

        os.makedirs(runtime_dir, exist_ok=True)
        runtime_session_file = os.path.join(runtime_dir, os.path.basename(expected_file))
        shutil.copy2(expected_file, runtime_session_file)

        # Return name without ".session" because Telethon will append it.
        return runtime_session_file[:-8] if runtime_session_file.endswith(".session") else runtime_session_file

    def assert_session_exists(self) -> None:
        expected_file = (
            self._session_path if self._session_path.endswith(".session") else f"{self._session_path}.session"
        )
        if not os.path.exists(expected_file):
            if self._tdata_path:
                # Load from tdata
                loader = TDataSessionLoader(self._tdata_path, self._session_path)
                asyncio.run(loader.load_client())  # This will create the session file
            else:
                raise RuntimeError(
                    f"Telegram session file not found at {expected_file!r}. "
                    f"Mount your authorized session file into the container or set TELEGRAM_TDATA_PATH to load from tdata."
                )


@dataclass(frozen=True)
class LastPostEvent:
    tg_channel_id: int
    message_id: int
    channel_identifier: str
    timestamp: int

    def to_payload(self) -> dict[str, Any]:
        return {
            "channel_id": self.tg_channel_id,
            "message_id": self.message_id,
            "channel_identifier": self.channel_identifier,
            "timestamp": self.timestamp
        }


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
        self._session = TelegramSessionManager(tg_config.session_path, tg_config.tdata_path)

        self._channel_id_by_peer: dict[int, int] = {}
        self._entity_by_channel_row_id: dict[int, Any] = {}
        self._logger = logging.getLogger(__name__)

    def _publish(self, event: LastPostEvent) -> None:
        key = str(event.tg_channel_id)
        self._producer.send_json(key=key, payload=event.to_payload())

    def _resolve_channel(self, client: TelegramClient, ch: TrackedChannel) -> tuple[int, Any]:
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
        """Process all active channels and publish new messages."""
        channels = self._repo.list_active()
        if not channels:
            self._logger.debug("No active channels to process")
            return
            
        self._logger.debug(f"Processing {len(channels)} channels")
            
        for ch in channels:
            try:
                peer_id, entity = self._resolve_channel(client, ch)
                messages = client.get_messages(entity, limit=1)
                
                if not messages:
                    self._logger.debug(f"No messages found for channel {ch.identifier}")
                    continue

                latest_message_id = int(messages[0].id)
                message_timestamp = int(messages[0].date.timestamp())
                
                self._logger.debug(f"Channel {ch.identifier}: latest={latest_message_id}, tracked={ch.last_message_id}")
                
                if latest_message_id > ch.last_message_id:
                    event = LastPostEvent(
                        tg_channel_id=peer_id, 
                        message_id=latest_message_id,
                        channel_identifier=ch.identifier,
                        timestamp=message_timestamp
                    )
                    self._publish(event)
                    self._repo.set_last_message_id(channel_id=ch.id, last_message_id=latest_message_id)
                    self._logger.info(f"Published new message for channel {ch.identifier}: {latest_message_id}")
                else:
                    self._logger.debug(f"No new messages for channel {ch.identifier}")
                    
            except FloodWaitError as e:
                self._logger.warning(f"Flood wait for channel {ch.identifier!r}: {e.seconds}s")
                time.sleep(e.seconds)
            except (ChannelPrivateError, ChatAdminRequiredError) as e:
                self._logger.error(f"Access denied for channel {ch.identifier!r}: {e}")
            except Exception as exc:
                self._logger.error(f"Error processing channel {ch.identifier!r}: {exc}", exc_info=True)

    def run(self) -> None:
        """Main execution loop for watching Telegram channels."""
        session_name = self._session.prepare_writable_session_name()
        self._logger.info("Starting Telegram client...")

        with TelegramClient(session_name, self._tg_config.api_id, self._tg_config.api_hash) as client:
            if not client.is_user_authorized():
                raise RuntimeError(
                    "Telegram client is not authorized. Provide a valid authorized session file."
                )

            self._logger.info("Client authorized, starting to poll for new posts...")
            
            # Initial tick to warm up caches
            self._tick_once(client)
            
            while True:
                try:
                    self._tick_once(client)
                except KeyboardInterrupt:
                    self._logger.info("Received interrupt signal, shutting down...")
                    break
                except Exception as exc:
                    self._logger.error(f"Unexpected error in main loop: {exc}", exc_info=True)
                    
                time.sleep(self._tick_seconds)

