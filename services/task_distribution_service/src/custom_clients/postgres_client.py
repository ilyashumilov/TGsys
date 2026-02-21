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

    async def get_available_account(self, min_health_score: int, cooldown_minutes: float) -> Optional[Dict[str, Any]]:
        """Get best available account based on health and load balancing."""
        if not self._pool:
            raise RuntimeError("Not connected to database")
        
        query = """
            SELECT id, phone_number,
                   proxy_type, proxy_host, proxy_port, proxy_username, proxy_password,
                   health_score, session_status, comments_count,
                   COALESCE(last_comment_time::text, 'never') as last_activity
            FROM telegram_accounts
            WHERE is_active = true 
              AND session_status = 'authorized'
              AND health_score >= $1
              AND (last_comment_time IS NULL 
                   OR last_comment_time < NOW() - INTERVAL '%s minutes')
            ORDER BY comments_count ASC, health_score DESC
            LIMIT 1
        """ % cooldown_minutes
        
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(query, min_health_score)
            return dict(row) if row else None

    async def get_available_accounts_list(self, min_health_score: int, cooldown_minutes: float) -> List[Dict[str, Any]]:
        """Get list of all available accounts for logging purposes."""
        if not self._pool:
            raise RuntimeError("Not connected to database")
        
        query = """
            SELECT id, phone_number,
                   proxy_type, proxy_host, proxy_port, proxy_username, proxy_password,
                   health_score, session_status, comments_count,
                   COALESCE(last_comment_time::text, 'never') as last_activity
            FROM telegram_accounts
            WHERE is_active = true 
              AND session_status = 'authorized'
              AND health_score >= $1
              AND (last_comment_time IS NULL 
                   OR last_comment_time < NOW() - INTERVAL '%s minutes')
            ORDER BY comments_count ASC, health_score DESC
            LIMIT 10
        """ % cooldown_minutes
        
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

    async def insert_pending_task(
        self, 
        channel_id: int, 
        message_id: int, 
        channel_identifier: str,
        post_text: str = "",
        post_date: str = ""
    ) -> int:
        """Insert a pending task for retry."""
        if not self._pool:
            raise RuntimeError("Not connected to database")
        
        query = """
            INSERT INTO pending_tasks (channel_id, message_id, channel_identifier, post_text, post_date)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING id
        """
        
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(query, channel_id, message_id, channel_identifier, post_text, post_date)
            return row['id'] if row else 0

    async def get_pending_tasks(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get oldest pending tasks for retry."""
        if not self._pool:
            raise RuntimeError("Not connected to database")
        
        query = """
            SELECT id, channel_id, message_id, channel_identifier, post_text, post_date, retry_count, created_at
            FROM pending_tasks
            ORDER BY created_at ASC
            LIMIT $1
        """
        
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query, limit)
            return [dict(row) for row in rows]

    async def delete_pending_task(self, task_id: int) -> bool:
        """Delete a pending task after successful assignment."""
        if not self._pool:
            raise RuntimeError("Not connected to database")
        
        query = """
            DELETE FROM pending_tasks
            WHERE id = $1
        """
        
        async with self._pool.acquire() as conn:
            result = await conn.execute(query, task_id)
            return result == "DELETE 1"

    async def increment_pending_task_retry(self, task_id: int) -> bool:
        """Increment retry count for a pending task."""
        if not self._pool:
            raise RuntimeError("Not connected to database")
        
        query = """
            UPDATE pending_tasks
            SET retry_count = retry_count + 1, updated_at = NOW()
            WHERE id = $1
        """
        
        async with self._pool.acquire() as conn:
            result = await conn.execute(query, task_id)
            return result == "UPDATE 1"
