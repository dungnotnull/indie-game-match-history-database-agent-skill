"""Schema versioning and migrations for the SQLite backend.

The in-memory backend is schemaless; this module is consumed by
:mod:`indie_match_history.storage.sqlite` to bring a database up to the
current schema version with forward-only migrations.
"""
from __future__ import annotations

import sqlite3
from typing import Callable

from .errors import SchemaVersionError

SCHEMA_VERSION = 3

Migration = Callable[[sqlite3.Connection], None]


def _v1_create(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS schema_meta (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS players (
            player_id TEXT PRIMARY KEY,
            handle TEXT NOT NULL UNIQUE,
            display_name TEXT,
            region TEXT,
            created_at TEXT NOT NULL,
            is_minor INTEGER NOT NULL DEFAULT 0,
            deleted INTEGER NOT NULL DEFAULT 0,
            metadata TEXT
        );
        CREATE TABLE IF NOT EXISTS matches (
            match_id TEXT PRIMARY KEY,
            game_id TEXT NOT NULL,
            mode TEXT,
            season TEXT,
            started_at TEXT NOT NULL,
            ended_at TEXT,
            duration_ms INTEGER,
            region TEXT,
            replay_id TEXT,
            metadata TEXT
        );
        CREATE TABLE IF NOT EXISTS match_results (
            match_id TEXT NOT NULL,
            player_id TEXT NOT NULL,
            team TEXT,
            outcome TEXT NOT NULL,
            score REAL,
            rating_before REAL,
            rating_after REAL,
            PRIMARY KEY (match_id, player_id)
        );
        CREATE TABLE IF NOT EXISTS match_events (
            event_id TEXT PRIMARY KEY,
            match_id TEXT NOT NULL,
            player_id TEXT,
            kind TEXT NOT NULL,
            ts TEXT NOT NULL,
            payload TEXT
        );
        CREATE TABLE IF NOT EXISTS replays (
            replay_id TEXT PRIMARY KEY,
            match_id TEXT,
            game_id TEXT NOT NULL,
            blob_path TEXT NOT NULL,
            size_bytes INTEGER NOT NULL,
            sha256 TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_players_handle ON players(handle);
        CREATE INDEX IF NOT EXISTS idx_matches_game_started ON matches(game_id, started_at DESC);
        CREATE INDEX IF NOT EXISTS idx_results_player ON match_results(player_id);
        CREATE INDEX IF NOT EXISTS idx_results_match ON match_results(match_id);
        CREATE INDEX IF NOT EXISTS idx_events_match ON match_events(match_id, ts);
        CREATE INDEX IF NOT EXISTS idx_replays_match ON replays(match_id);
        """
    )


def _v2_add_season_idx(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE INDEX IF NOT EXISTS idx_matches_season ON matches(game_id, season, started_at DESC);
        CREATE TABLE IF NOT EXISTS rating_snapshots (
            player_id TEXT NOT NULL,
            match_id TEXT NOT NULL,
            system TEXT NOT NULL,
            rating REAL NOT NULL,
            rd REAL,
            vol REAL,
            ts TEXT NOT NULL,
            PRIMARY KEY (player_id, match_id, system)
        );
        CREATE INDEX IF NOT EXISTS idx_snapshots_player_ts ON rating_snapshots(player_id, ts DESC);
        """
    )


def _v3_nullable_seed_match(conn: sqlite3.Connection) -> None:
    """Allow NULL match_id on rating_snapshots so seed (registration) ratings
    can be stored without an associated match, while keeping a unique index
    that supports upserts for real match snapshots."""
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS rating_snapshots_new (
            player_id TEXT NOT NULL,
            match_id TEXT,
            system TEXT NOT NULL,
            rating REAL NOT NULL,
            rd REAL,
            vol REAL,
            ts TEXT NOT NULL
        );
        INSERT INTO rating_snapshots_new(player_id, match_id, system, rating, rd, vol, ts)
        SELECT player_id, match_id, system, rating, rd, vol, ts FROM rating_snapshots;
        DROP TABLE rating_snapshots;
        ALTER TABLE rating_snapshots_new RENAME TO rating_snapshots;
        CREATE UNIQUE INDEX IF NOT EXISTS idx_snapshots_upsert
            ON rating_snapshots(player_id, match_id, system);
        CREATE INDEX IF NOT EXISTS idx_snapshots_player_ts
            ON rating_snapshots(player_id, ts DESC);
        """
    )


_MIGRATIONS: list[tuple[int, Migration]] = [
    (1, _v1_create),
    (2, _v2_add_season_idx),
    (3, _v3_nullable_seed_match),
]


def current_version(conn: sqlite3.Connection) -> int:
    """Return the persisted schema version (0 if none yet)."""
    try:
        row = conn.execute(
            "SELECT value FROM schema_meta WHERE key = 'version'"
        ).fetchone()
    except sqlite3.OperationalError:
        return 0
    return int(row[0]) if row else 0


def migrate(conn: sqlite3.Connection, target: int = SCHEMA_VERSION) -> int:
    """Migrate ``conn`` forward to ``target`` (default: current schema version).

    Returns the new version. Raises :class:`SchemaVersionError` if the stored
    version is ahead of ``target`` (downgrades are unsupported).
    """
    with conn:  # transactional
        conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
        )
        version = current_version(conn)
        if version > target:
            raise SchemaVersionError(
                f"database version {version} is ahead of target {target}; downgrade unsupported"
            )
        for step_version, migration in _MIGRATIONS:
            if version < step_version <= target:
                migration(conn)
                version = step_version
                conn.execute(
                    "INSERT INTO schema_meta(key, value) VALUES('version', ?) "
                    "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                    (str(version),),
                )
        return version