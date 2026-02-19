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

    async def get_active_accounts(self) -> List[Dict[str, Any]]:
        """Get all active accounts."""
        if not self._pool:
            raise RuntimeError("Not connected to database")
        
        query = """
            SELECT id, api_id, api_hash, account_name, user_id, first_name, last_name, username, phone_number, session_file,
                   proxy_type, proxy_host, proxy_port, proxy_username, proxy_password,
                   health_score, session_status
            FROM telegram_accounts
            WHERE is_active = true
            ORDER BY id
        """
        
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query)
            return [dict(row) for row in rows]

    async def get_account(self, account_id: int) -> Optional[Dict[str, Any]]:
        """Get specific account by ID."""
        if not self._pool:
            raise RuntimeError("Not connected to database")
        
        query = """
            SELECT id, api_id, api_hash, account_name, user_id, first_name, last_name, username, phone_number, session_file,
                   proxy_type, proxy_host, proxy_port, proxy_username, proxy_password,
                   health_score, session_status, is_active
            FROM telegram_accounts
            WHERE id = $1
        """
        
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(query, account_id)
            return dict(row) if row else None

    async def insert_account(self, account_data: Dict[str, Any]) -> int:
        """Insert new account and return ID."""
        if not self._pool:
            raise RuntimeError("Not connected to database")
        
        query = """
            INSERT INTO telegram_accounts 
            (account_name, user_id, first_name, last_name, username, phone_number, session_file,
             proxy_type, proxy_host, proxy_port, proxy_username, proxy_password, session_status)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
            RETURNING id
        """
        
        async with self._pool.acquire() as conn:
            result = await conn.fetchrow(
                query,
                account_data['account_name'],
                account_data.get('user_id'),
                account_data.get('first_name'),
                account_data.get('last_name'),
                account_data.get('username'),
                account_data.get('phone_number'),
                account_data.get('session_file'),
                account_data.get('proxy_type'),
                account_data.get('proxy_host'),
                account_data.get('proxy_port'),
                account_data.get('proxy_username'),
                account_data.get('proxy_password'),
                account_data.get('session_status', 'unknown')
            )
            return result['id']

    async def update_account_health(self, account_id: int, health_score: int) -> bool:
        """Update account health score."""
        if not self._pool:
            raise RuntimeError("Not connected to database")
        
        query = """
            UPDATE telegram_accounts
            SET health_score = $2, updated_at = NOW()
            WHERE id = $1
        """
        
        async with self._pool.acquire() as conn:
            result = await conn.execute(query, account_id, health_score)
            return result == "UPDATE 1"

    async def deactivate_account(self, account_id: int) -> bool:
        """Deactivate an account."""
        if not self._pool:
            raise RuntimeError("Not connected to database")
        
        query = """
            UPDATE telegram_accounts
            SET is_active = false, updated_at = NOW()
            WHERE id = $1
        """
        
        async with self._pool.acquire() as conn:
            result = await conn.execute(query, account_id)
            return result == "UPDATE 1"
