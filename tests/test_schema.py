"""Tests for schema versioning & migration logic."""
from __future__ import annotations

import sqlite3

import pytest

from indie_match_history.errors import SchemaVersionError
from indie_match_history.schema import SCHEMA_VERSION, current_version, migrate


def test_fresh_db_migrates_to_latest():
    conn = sqlite3.connect(":memory:")
    v = migrate(conn)
    assert v == SCHEMA_VERSION
    assert current_version(conn) == SCHEMA_VERSION
    conn.close()


def test_idempotent_migration():
    conn = sqlite3.connect(":memory:")
    migrate(conn)
    v = migrate(conn)  # second call is a no-op
    assert v == SCHEMA_VERSION
    conn.close()


def test_downgrade_rejected():
    conn = sqlite3.connect(":memory:")
    migrate(conn)
    with pytest.raises(SchemaVersionError):
        migrate(conn, target=1)
    conn.close()


def test_target_partial_migration():
    conn = sqlite3.connect(":memory:")
    v = migrate(conn, target=1)
    assert v == 1
    # players table exists from v1
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    assert ("players",) in rows
    conn.close()