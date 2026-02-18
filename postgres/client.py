from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

import psycopg2
import psycopg2.extras


@dataclass(frozen=True)
class PostgresConnection:
    host: str
    port: int
    db: str
    user: str
    password: str


class PostgresClient:
    """
    Small sync DB helper with basic CRUD-style utilities.
    Intended to be reused by multiple services.
    """

    def __init__(self, conn: PostgresConnection):
        self._conn = conn

    def _connect(self):
        return psycopg2.connect(
            host=self._conn.host,
            port=self._conn.port,
            dbname=self._conn.db,
            user=self._conn.user,
            password=self._conn.password,
        )

    def fetch_all(self, sql: str, params: Iterable[Any] | None = None) -> list[dict[str, Any]]:
        with self._connect() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(sql, params)
                rows = cur.fetchall()
                return [dict(r) for r in rows]

    def fetch_one(self, sql: str, params: Iterable[Any] | None = None) -> dict[str, Any] | None:
        with self._connect() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(sql, params)
                row = cur.fetchone()
                return dict(row) if row is not None else None

    def execute(self, sql: str, params: Iterable[Any] | None = None) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
            conn.commit()


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

