from __future__ import annotations

from dataclasses import dataclass

from postgres.client import BaseRepository, PostgresClient


@dataclass(frozen=True)
class TrackedChannel:
    id: int
    identifier: str
    tg_channel_id: int | None
    last_message_id: int


class ChannelRepository(BaseRepository):
    """
    Repository for `telegram_channels` table.
    """

    def __init__(self, db: PostgresClient):
        super().__init__(db, table="telegram_channels")

    def list_active(self) -> list[TrackedChannel]:
        rows = self._db.fetch_all(
            """
            SELECT id, identifier, tg_channel_id, last_message_id
            FROM telegram_channels
            WHERE is_active = TRUE
            ORDER BY id
            """
        )
        return [
            TrackedChannel(
                id=int(r["id"]),
                identifier=str(r["identifier"]),
                tg_channel_id=int(r["tg_channel_id"]) if r["tg_channel_id"] is not None else None,
                last_message_id=int(r["last_message_id"] or 0),
            )
            for r in rows
        ]

    def update_peer_id(self, channel_id: int, tg_channel_id: int) -> None:
        self._db.execute(
            """
            UPDATE telegram_channels
            SET tg_channel_id = %s, updated_at = NOW()
            WHERE id = %s
            """,
            (tg_channel_id, channel_id),
        )

    def set_last_message_id(self, channel_id: int, last_message_id: int) -> None:
        self._db.execute(
            """
            UPDATE telegram_channels
            SET last_message_id = %s, updated_at = NOW()
            WHERE id = %s
            """,
            (last_message_id, channel_id),
        )

    def set_last_message_id_by_peer(self, tg_channel_id: int, last_message_id: int) -> None:
        self._db.execute(
            """
            UPDATE telegram_channels
            SET last_message_id = %s, updated_at = NOW()
            WHERE tg_channel_id = %s
            """,
            (last_message_id, tg_channel_id),
        )

