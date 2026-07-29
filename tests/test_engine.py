"""Tests for the MatchHistoryEngine facade."""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from indie_match_history import (
    EngineConfig, MatchHistoryEngine, MatchOutcome, MatchResult, RatingSystem,
)
from indie_match_history.errors import ConfigurationError, NotFoundError, ValidationError
from indie_match_history.storage import InMemoryStorage
from tests.conftest import make_two_players, two_player_match


def test_register_seeds_rating(engine: MatchHistoryEngine):
    a = engine.register_player("alice")
    rating = engine.player_rating(a.player_id)
    assert rating.value == engine.rating_engine.default_rating().value


def test_record_match_updates_ratings_and_leaderboard(engine: MatchHistoryEngine):
    a, b = make_two_players(engine)
    res = engine.record_match("pong", two_player_match(a, b, a_wins=True), season="s1")
    deltas = res.rating_deltas
    assert deltas[a.player_id][1] > deltas[a.player_id][0]
    assert deltas[b.player_id][1] < deltas[b.player_id][0]
    lb = engine.leaderboard("pong", "s1", top=5)
    assert lb[0].member == a.player_id
    assert lb[1].member == b.player_id


def test_record_match_rejects_unregistered_player(engine: MatchHistoryEngine):
    with pytest.raises(NotFoundError):
        engine.record_match("pong", [
            MatchResult("pl_ghost", MatchOutcome.WIN),
            MatchResult("pl_other", MatchOutcome.LOSS),
        ], season="s1")


def test_record_match_rejects_empty_results(engine: MatchHistoryEngine):
    with pytest.raises(ValidationError):
        engine.record_match("pong", [], season="s1")


def test_casual_match_skips_ratings(engine: MatchHistoryEngine):
    a, b = make_two_players(engine)
    before = engine.player_rating(a.player_id).value
    engine.record_match("pong", two_player_match(a, b, a_wins=True),
                        mode="casual", season="s1")
    after = engine.player_rating(a.player_id).value
    assert before == after
    assert engine.leaderboard("pong", "s1") == []


def test_leaderboard_around(engine: MatchHistoryEngine):
    players = [engine.register_player(f"p{i}") for i in range(5)]
    # give them distinct ratings via wins
    for i in range(4):
        engine.record_match("pong", [
            MatchResult(players[i].player_id, MatchOutcome.WIN),
            MatchResult(players[4].player_id, MatchOutcome.LOSS),
        ], season="s1")
    around = engine.leaderboard_around("pong", "s1", players[2].player_id, window=1)
    assert players[2].player_id in [e.member for e in around]


def test_player_history_and_rating_history(engine: MatchHistoryEngine):
    a, b = make_two_players(engine)
    engine.record_match("pong", two_player_match(a, b, True), season="s1")
    engine.record_match("pong", two_player_match(a, b, False), season="s1")
    history = engine.player_history(a.player_id)
    assert len(history) == 2
    rh = engine.player_rating_history(a.player_id)
    # seed + 2 match snapshots = 3
    assert len(rh) == 3


def test_attach_and_load_replay(engine: MatchHistoryEngine):
    if engine.replay_store is None:
        pytest.skip("no replay store on memory engine without root")
    a, b = make_two_players(engine)
    res = engine.record_match("pong", two_player_match(a, b, True), season="s1")
    cfg = engine.config.replay
    blob = cfg.magic + b"frame" * 200
    ref = engine.attach_replay(res.match.match_id, blob)
    assert engine.load_replay(ref.replay_id) == blob
    # match now references the replay
    assert engine.get_match(res.match.match_id).replay_id == ref.replay_id


def test_attach_replay_without_store_raises():
    eng = MatchHistoryEngine(storage=InMemoryStorage())
    a = eng.register_player("a"); b = eng.register_player("b")
    res = eng.record_match("pong", two_player_match(a, b, True), season="s1")
    with pytest.raises(ConfigurationError):
        eng.attach_replay(res.match.match_id, b"x" * 10)


def test_engine_stats(engine: MatchHistoryEngine):
    a, b = make_two_players(engine)
    engine.record_match("pong", two_player_match(a, b, True), season="s1")
    s = engine.stats()
    assert s["matches"] == 1
    assert s["players"] == 2
    assert s["rating_system"] == engine.config.rating_system


def test_rating_system_mismatch_raises():
    from indie_match_history.ratings import Glicko2Engine
    with pytest.raises(ConfigurationError):
        MatchHistoryEngine(
            storage=InMemoryStorage(),
            config=EngineConfig(rating_system="elo"),
            rating_engine=Glicko2Engine(),
        )


def test_invalid_rating_system_config():
    with pytest.raises(ConfigurationError):
        EngineConfig(rating_system="trueskill")


def test_glicko2_engine_end_to_end(tmp_path):
    cfg = EngineConfig(rating_system="glicko2", sqlite_path=tmp_path / "g.db")
    with MatchHistoryEngine(config=cfg) as eng:
        a = eng.register_player("alice")
        b = eng.register_player("bob")
        res = eng.record_match("pong", two_player_match(a, b, True), season="s1")
        assert res.rating_deltas[a.player_id][1] > 1500
        rating = eng.player_rating(a.player_id)
        assert rating.system == RatingSystem.GLICKO2
        assert rating.rd > 0