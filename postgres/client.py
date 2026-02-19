from __future__ import annotations

import logging
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Iterable

import psycopg2
import psycopg2.extras
import psycopg2.pool


@dataclass(frozen=True)
class PostgresConnection:
    host: str
    port: int
    db: str
    user: str
    password: str


class PostgresClient:
    """
    Enhanced DB helper with connection pooling and basic CRUD-style utilities.
    Intended to be reused across multiple services.
    """

    def __init__(self, conn: PostgresConnection, min_conn: int = 1, max_conn: int = 10):
        self._conn = conn
        self._logger = logging.getLogger(__name__)
        self._pool = psycopg2.pool.ThreadedConnectionPool(
            min_conn, max_conn,
            host=conn.host,
            port=conn.port,
            dbname=conn.db,
            user=conn.user,
            password=conn.password,
        )
        self._logger.info(f"Initialized connection pool: {min_conn}-{max_conn} connections")

    @contextmanager
    def _get_connection(self):
        """Get a connection from the pool."""
        conn = None
        try:
            conn = self._pool.getconn()
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            self._logger.error(f"Database connection error: {e}")
            raise
        finally:
            if conn:
                self._pool.putconn(conn)

    def fetch_all(self, sql: str, params: Iterable[Any] | None = None) -> list[dict[str, Any]]:
        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(sql, params)
                rows = cur.fetchall()
                return [dict(r) for r in rows]

    def fetch_one(self, sql: str, params: Iterable[Any] | None = None) -> dict[str, Any] | None:
        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(sql, params)
                row = cur.fetchone()
                return dict(row) if row is not None else None

    def execute(self, sql: str, params: Iterable[Any] | None = None) -> None:
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
            conn.commit()

    def close(self) -> None:
        """Close all connections in the pool."""
        if self._pool:
            self._pool.closeall()
            self._logger.info("Database connection pool closed")


class BaseRepository:
    """
    Generic CRUD-style repository that can be subclassed per service.
    """

    def __init__(self, db: PostgresClient, table: str, pk: str = "id"):
        self._db = db
        self._table = table
        self._pk = pk

    def get(self, id_value: Any) -> dict[str, Any] | None:
        return self._db.fetch_one(
            f"SELECT * FROM {self._table} WHERE {self._pk} = %s",
            (id_value,),
        )

    def list_all(self) -> list[dict[str, Any]]:
        return self._db.fetch_all(f"SELECT * FROM {self._table}", None)

    def insert(self, data: dict[str, Any]) -> None:
        cols = ", ".join(data.keys())
        placeholders = ", ".join(["%s"] * len(data))
        sql = f"INSERT INTO {self._table} ({cols}) VALUES ({placeholders})"
        self._db.execute(sql, tuple(data.values()))

    def update(self, id_value: Any, data: dict[str, Any]) -> None:
        assignments = ", ".join(f"{col} = %s" for col in data.keys())
        sql = f"UPDATE {self._table} SET {assignments} WHERE {self._pk} = %s"
        params = list(data.values()) + [id_value]
        self._db.execute(sql, params)

