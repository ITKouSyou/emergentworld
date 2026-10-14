"""数据库会话工厂 + schema 增量升级。"""

from __future__ import annotations

from sqlalchemy import text
from sqlmodel import Session, create_engine

from server.config import settings

from sqlalchemy.pool import NullPool

engine = create_engine(
    f"sqlite:///{settings.db_path}",
    echo=False,
    poolclass=NullPool,
    connect_args={
        "timeout": 30,
        "check_same_thread": False,
    },
)


def get_session() -> Session:
    return Session(engine)


def _has_column(conn, table: str, column: str) -> bool:
    rows = conn.execute(text("PRAGMA table_info(%s)" % table)).fetchall()
    if not rows:
        return True
    return column in {r[1] for r in rows}


def _add_col(conn, table: str, col: str, ddl: str) -> None:
    if not _has_column(conn, table, col):
        conn.execute(text("ALTER TABLE %s ADD COLUMN %s" % (table, ddl)))


def ensure_schema() -> None:
    with engine.begin() as conn:
        # item
        _add_col(conn, "item", "owner_id", "owner_id TEXT NOT NULL DEFAULT ''")
        _add_col(conn, "item", "consumed", "consumed INTEGER NOT NULL DEFAULT 0")
        # memory
        _add_col(conn, "memory", "embedding_json", "embedding_json TEXT NOT NULL DEFAULT '[]'")
        # npc
        _add_col(conn, "npc", "gender", "gender TEXT NOT NULL DEFAULT 'unknown'")
        _add_col(conn, "npc", "family_json", "family_json TEXT NOT NULL DEFAULT '{}'")
        _add_col(conn, "npc", "schedule_json", "schedule_json TEXT NOT NULL DEFAULT '{}'")
        _add_col(conn, "npc", "impressions_json", "impressions_json TEXT NOT NULL DEFAULT '{}'")
        _add_col(conn, "npc", "faction", "faction TEXT NOT NULL DEFAULT 'neutral'")
        _add_col(conn, "player", "money", "money INTEGER NOT NULL DEFAULT 0")
        _add_col(conn, "player", "factions_json", "factions_json TEXT NOT NULL DEFAULT '{}'")
        # world
        _add_col(conn, "world", "season", "season TEXT NOT NULL DEFAULT 'spring'")
        _add_col(conn, "world", "weather", "weather TEXT NOT NULL DEFAULT 'clear'")
        _add_col(conn, "world", "weather_changed_tick",
                 "weather_changed_tick INTEGER NOT NULL DEFAULT 0")
        _add_col(conn, "world", "last_social_tick",
                 "last_social_tick INTEGER NOT NULL DEFAULT -999")
        _add_col(conn, "world", "social_count_today",
                 "social_count_today INTEGER NOT NULL DEFAULT 0")
        _add_col(conn, "relationship", "kind", "kind TEXT NOT NULL DEFAULT ''")
