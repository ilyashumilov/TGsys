from __future__ import annotations

import logging
from typing import Any, Iterable

from postgres.client import PostgresClient, PostgresConnection


class PostgresResultClient:
    """Custom Postgres client for task result service."""

    def __init__(self, conn: PostgresConnection):
        self._client = PostgresClient(conn)
        self._logger = logging.getLogger(__name__)

    def execute(self, sql: str, params: Iterable[Any] | None = None) -> None:
        """Execute a SQL statement."""
        try:
            self._client.execute(sql, params)
            self._logger.debug(f"Executed SQL: {sql}")
        except Exception as e:
            self._logger.error(f"Failed to execute SQL: {sql}, error: {e}")
            raise

    def fetch_one(self, sql: str, params: Iterable[Any] | None = None) -> dict[str, Any] | None:
        """Fetch one row."""
        try:
            result = self._client.fetch_one(sql, params)
            self._logger.debug(f"Fetched one row with SQL: {sql}")
            return result
        except Exception as e:
            self._logger.error(f"Failed to fetch one row with SQL: {sql}, error: {e}")
            raise

    def fetch_all(self, sql: str, params: Iterable[Any] | None = None) -> list[dict[str, Any]]:
        """Fetch all rows."""
        try:
            result = self._client.fetch_all(sql, params)
            self._logger.debug(f"Fetched {len(result)} rows with SQL: {sql}")
            return result
        except Exception as e:
            self._logger.error(f"Failed to fetch all rows with SQL: {sql}, error: {e}")
            raise

    def close(self) -> None:
        """Close the client."""
        self._client.close()
