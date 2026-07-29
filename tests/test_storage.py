"""Tests for storage backends (in-memory + SQLite)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from indie_match_history import (
    Match, MatchEvent, MatchOutcome, MatchResult, Player, Rating, RatingSystem,
)
from indie_match_history.errors import ConflictError, NotFoundError
from indie_match_history.storage import InMemoryStorage, SQLiteStorage, StorageTier
from indie_match_history.storage.base import PlayerRatingRecord
from indie_match_history.utils import utcnow

BACKENDS = [InMemoryStorage, lambda: SQLiteStorage(":memory:")]


@pytest.fixture(params=BACKENDS, ids=["memory", "sqlite"])
def backend(request):
    store = request.param()
    yield store
    store.close()


def _player(pid: str = "pl_1", handle: str = "alice") -> Player:
    return Player(player_id=pid, handle=handle, created_at=utcnow())


def _match(mid: str = "m1", a: str = "pl_1", b: str = "pl_2") -> Match:
    ts = utcnow()
    return Match(match_id=mid, game_id="pong", started_at=ts, season="s1",
                 results=(MatchResult(a, MatchOutcome.WIN),
                          MatchResult(b, MatchOutcome.LOSS)))


def test_player_upsert_get(backend):
    backend.upsert_player(_player())
    assert backend.get_player("pl_1").handle == "alice"
    assert backend.get_player_by_handle("alice").player_id == "pl_1"
    with pytest.raises(NotFoundError):
        backend.get_player("missing")


def test_player_handle_conflict(backend):
    backend.upsert_player(_player("pl_1", "alice"))
    with pytest.raises(ConflictError):
        backend.upsert_player(_player("pl_2", "alice"))


def test_insert_and_get_match(backend):
    backend.upsert_player(_player("pl_1", "alice"))
    backend.upsert_player(_player("pl_2", "bob"))
    backend.insert_match(_match())
    m = backend.get_match("m1")
    assert m.game_id == "pong"
    assert backend.count_matches() == 1
    assert backend.count_matches("pong") == 1
    assert backend.count_matches("other") == 0


def test_duplicate_match_conflict(backend):
    backend.upsert_player(_player("pl_1", "alice"))
    backend.upsert_player(_player("pl_2", "bob"))
    backend.insert_match(_match())
    with pytest.raises(ConflictError):
        backend.insert_match(_match())


def test_player_history_filtering(backend):
    backend.upsert_player(_player("pl_1", "alice"))
    backend.upsert_player(_player("pl_2", "bob"))
    backend.upsert_player(_player("pl_3", "carol"))
    backend.insert_match(_match("m1", "pl_1", "pl_2"))
    backend.insert_match(_match("m2", "pl_1", "pl_3"))
    backend.insert_match(_match("m3", "pl_2", "pl_3"))
    history = backend.player_history("pl_1")
    assert {m.match_id for m in history} == {"m1", "m2"}
    assert len(backend.list_matches(season="s1")) == 3
    assert len(backend.list_matches(game_id="pong", limit=2)) == 2


def test_events(backend):
    backend.upsert_player(_player("pl_1", "alice"))
    backend.upsert_player(_player("pl_2", "bob"))
    backend.insert_match(_match())
    ev = MatchEvent(event_id="e1", match_id="m1", kind="kill", ts=utcnow(),
                    player_id="pl_1")
    n = backend.insert_events([ev])
    assert n == 1
    events = backend.list_events("m1")
    assert len(events) == 1 and events[0].kind == "kill"
    with pytest.raises(NotFoundError):
        backend.insert_events([MatchEvent(event_id="e2", match_id="ghost",
                                          kind="x", ts=utcnow())])


def test_rating_snapshots(backend):
    backend.upsert_player(_player())
    rec = PlayerRatingRecord(
        player_id="pl_1",
        rating=Rating(value=1500.0, rd=50.0, vol=0.06, system=RatingSystem.GLICKO2),
        match_id="m_x", ts=utcnow(),
    )
    backend.save_rating(rec)
    latest = backend.latest_rating("pl_1")
    assert latest is not None and latest.value == 1500.0
    hist = backend.rating_history("pl_1")
    assert len(hist) == 1
    assert backend.latest_rating("nobody") is None


def test_seed_rating_with_null_match(backend):
    """Registration seed ratings have match_id=None and must persist."""
    backend.upsert_player(_player())
    backend.save_rating(PlayerRatingRecord(
        player_id="pl_1",
        rating=Rating(value=1200.0),
        match_id=None, ts=utcnow(),
    ))
    assert backend.latest_rating("pl_1").value == 1200.0


def test_tier_default_and_set(backend):
    backend.upsert_player(_player("pl_1", "alice"))
    backend.upsert_player(_player("pl_2", "bob"))
    backend.insert_match(_match())
    assert backend.get_match_tier("m1") == StorageTier.HOT
    backend.set_match_tier("m1", StorageTier.COLD)
    assert backend.get_match_tier("m1") == StorageTier.COLD


def test_purge_player_removes_solo_matches(backend):
    backend.upsert_player(_player("pl_1", "alice"))
    backend.upsert_player(_player("pl_2", "bob"))
    backend.insert_match(_match("m1", "pl_1", "pl_2"))
    summary = backend.purge_player_data("pl_1")
    assert summary["players"] == 1
    assert summary["matches"] == 1
    with pytest.raises(NotFoundError):
        backend.get_player("pl_1")
    with pytest.raises(NotFoundError):
        backend.get_match("m1")


def test_purge_player_anonymizes_team_matches(backend):
    for pid, h in [("pl_1", "a"), ("pl_2", "b"), ("pl_3", "c"), ("pl_4", "d")]:
        backend.upsert_player(_player(pid, h))
    ts = utcnow()
    m = Match(match_id="m_team", game_id="pong", started_at=ts,
              results=(MatchResult("pl_1", MatchOutcome.WIN, team="red"),
                       MatchResult("pl_2", MatchOutcome.WIN, team="red"),
                       MatchResult("pl_3", MatchOutcome.LOSS, team="blue"),
                       MatchResult("pl_4", MatchOutcome.LOSS, team="blue")))
    backend.insert_match(m)
    summary = backend.purge_player_data("pl_1")
    assert summary["players"] == 1
    # 4-player match is kept but anonymized
    kept = backend.get_match("m_team")
    pids = kept.participant_ids()
    assert "<purged>" in pids
    assert "pl_2" in pids


def test_sqlite_schema_version():
    store = SQLiteStorage(":memory:")
    from indie_match_history.schema import SCHEMA_VERSION, current_version
    assert current_version(store._conn) == SCHEMA_VERSION
    store.close()


def test_sqlite_migration_rejects_downgrade():
    store = SQLiteStorage(":memory:")
    from indie_match_history.errors import SchemaVersionError
    from indie_match_history.schema import migrate
    with pytest.raises(SchemaVersionError):
        migrate(store._conn, target=1)
    store.close()