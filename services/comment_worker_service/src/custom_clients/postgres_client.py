from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Optional

import asyncpg


@dataclass
class PostgresConnection:
    host: str
    port: int
    database: str
    user: str
    password: str


class PostgresClient:
    def __init__(self, connection: PostgresConnection):
        self._connection = connection
        self._pool: Optional[asyncpg.Pool] = None
        self._logger = logging.getLogger(__name__)

    async def connect(self) -> None:
        """Create connection pool."""
        try:
            self._pool = await asyncpg.create_pool(
                host=self._connection.host,
                port=self._connection.port,
                database=self._connection.database,
                user=self._connection.user,
                password=self._connection.password,
                min_size=2,
                max_size=10,
            )
            self._logger.info("Connected to PostgreSQL")
        except Exception as e:
            self._logger.error(f"Failed to connect to PostgreSQL: {e}")
            raise

    async def close(self) -> None:
        """Close connection pool."""
        if self._pool:
            await self._pool.close()
            self._logger.info("PostgreSQL connection closed")

    async def update_account_stats(self, account_id: int) -> bool:
        """Update account stats after successful comment."""
        if not self._pool:
            raise RuntimeError("Not connected to database")
        
        query = """
            UPDATE telegram_accounts
            SET last_comment_time = NOW(),
                comments_count = comments_count + 1,
                health_score = LEAST(100, health_score + 1),
                updated_at = NOW()
            WHERE id = $1
        """
        
        async with self._pool.acquire() as conn:
            result = await conn.execute(query, account_id)
            return result == "UPDATE 1"

    async def update_account_health(self, account_id: int, health_delta: int) -> bool:
        """Update account health score by delta."""
        if not self._pool:
            raise RuntimeError("Not connected to database")
        
        query = """
            UPDATE telegram_accounts
            SET health_score = GREATEST(0, LEAST(100, health_score + $2)),
                updated_at = NOW()
            WHERE id = $1
        """
        
        async with self._pool.acquire() as conn:
            result = await conn.execute(query, account_id, health_delta)
            return result == "UPDATE 1"
