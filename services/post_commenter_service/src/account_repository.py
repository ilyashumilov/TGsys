from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional

from custom_clients.postgres_client import BaseRepository, PostgresClient


@dataclass(frozen=True)
class TelegramAccount:
    id: int
    api_id: int
    api_hash: str
    phone_number: Optional[str]
    is_active: bool
    last_comment_at: Optional[datetime]
    cooldown_until: Optional[datetime]
    session_status: str
    proxy_type: Optional[str]
    proxy_host: Optional[str]
    proxy_port: Optional[int]
    proxy_username: Optional[str]
    proxy_password: Optional[str]
    created_at: datetime
    updated_at: datetime


class AccountRepository(BaseRepository):
    """Repository for managing Telegram accounts."""

    def __init__(self, db: PostgresClient):
        super().__init__(db, "telegram_accounts")
        self._logger = logging.getLogger(__name__)

    def get_active_accounts(self) -> List[TelegramAccount]:
        """Get all active and authorized accounts not in cooldown."""
        query = """
            SELECT id, api_id, api_hash, phone_number, is_active, 
                   last_comment_at, cooldown_until, session_status,
                   proxy_type, proxy_host, proxy_port, proxy_username, proxy_password,
                   created_at, updated_at
            FROM telegram_accounts 
            WHERE is_active = TRUE 
              AND session_status = 'authorized'
              AND (cooldown_until IS NULL OR cooldown_until <= NOW())
            ORDER BY RANDOM()
        """
        
        results = self._db.fetch_all(query)
        return [
            TelegramAccount(
                id=row["id"],
                api_id=row["api_id"],
                api_hash=row["api_hash"],
                phone_number=row["phone_number"],
                is_active=row["is_active"],
                last_comment_at=row["last_comment_at"],
                cooldown_until=row["cooldown_until"],
                session_status=row["session_status"],
                proxy_type=row["proxy_type"],
                proxy_host=row["proxy_host"],
                proxy_port=row["proxy_port"],
                proxy_username=row["proxy_username"],
                proxy_password=row["proxy_password"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
            for row in results
        ]

    def get_all_accounts(self) -> List[TelegramAccount]:
        """Get all accounts for status checking."""
        query = """
            SELECT id, api_id, api_hash, phone_number, is_active, 
                   last_comment_at, cooldown_until, session_status,
                   created_at, updated_at
            FROM telegram_accounts 
            ORDER BY api_id
        """
        
        results = self._db.fetch_all(query)
        return [
            TelegramAccount(
                id=row["id"],
                api_id=row["api_id"],
                api_hash=row["api_hash"],
                phone_number=row["phone_number"],
                is_active=row["is_active"],
                last_comment_at=row["last_comment_at"],
                cooldown_until=row["cooldown_until"],
                session_status=row["session_status"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
            for row in results
        ]

    def set_cooldown(self, account_id: int, cooldown_until: datetime) -> None:
        """Set cooldown for an account."""
        query = """
            UPDATE telegram_accounts 
            SET cooldown_until = %s, 
                last_comment_at = NOW(),
                updated_at = NOW()
            WHERE id = %s
        """
        self._db.execute(query, (cooldown_until, account_id))
        self._logger.info(f"Set cooldown for account {account_id} until {cooldown_until}")

    def update_session_status(self, account_id: int, status: str) -> None:
        """Update session status for an account."""
        query = """
            UPDATE telegram_accounts 
            SET session_status = %s, 
                updated_at = NOW()
            WHERE id = %s
        """
        self._db.execute(query, (status, account_id))
        self._logger.info(f"Updated session status for account {account_id} to {status}")

    def add_account(self, api_id: int, api_hash: str, phone_number: Optional[str] = None) -> int:
        """Add a new Telegram account."""
        query = """
            INSERT INTO telegram_accounts (api_id, api_hash, phone_number)
            VALUES (%s, %s, %s)
            ON CONFLICT (api_id) DO UPDATE SET
                api_hash = EXCLUDED.api_hash,
                phone_number = EXCLUDED.phone_number,
                updated_at = NOW()
            RETURNING id
        """
        result = self._db.fetch_one(query, (api_id, api_hash, phone_number))
        account_id = result["id"]
        self._logger.info(f"Added/updated account with API ID {api_id}, ID: {account_id}")
        return account_id
