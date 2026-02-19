from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import List, Optional, Dict, Any

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
                min_size=5,
                max_size=20,
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

    async def get_available_account(self, min_health_score: int, cooldown_hours: int) -> Optional[Dict[str, Any]]:
        """Get best available account based on health and load balancing."""
        if not self._pool:
            raise RuntimeError("Not connected to database")
        
        query = """
            SELECT id, api_id, api_hash, phone_number,
                   proxy_type, proxy_host, proxy_port, proxy_username, proxy_password,
                   health_score, session_status, comments_count,
                   COALESCE(last_comment_time::text, 'never') as last_activity
            FROM telegram_accounts
            WHERE is_active = true 
              AND session_status = 'authorized'
              AND health_score >= $1
              AND (last_comment_time IS NULL 
                   OR last_comment_time < NOW() - INTERVAL '%s hours')
            ORDER BY comments_count ASC, health_score DESC
            LIMIT 1
        """ % cooldown_hours
        
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(query, min_health_score)
            return dict(row) if row else None

    async def get_available_accounts_list(self, min_health_score: int, cooldown_hours: int) -> List[Dict[str, Any]]:
        """Get list of all available accounts for logging purposes."""
        if not self._pool:
            raise RuntimeError("Not connected to database")
        
        query = """
            SELECT id, api_id, api_hash, phone_number,
                   proxy_type, proxy_host, proxy_port, proxy_username, proxy_password,
                   health_score, session_status, comments_count,
                   COALESCE(last_comment_time::text, 'never') as last_activity
            FROM telegram_accounts
            WHERE is_active = true 
              AND session_status = 'authorized'
              AND health_score >= $1
              AND (last_comment_time IS NULL 
                   OR last_comment_time < NOW() - INTERVAL '%s hours')
            ORDER BY comments_count ASC, health_score DESC
            LIMIT 10
        """ % cooldown_hours
        
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query, min_health_score)
            return [dict(row) for row in rows]

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
