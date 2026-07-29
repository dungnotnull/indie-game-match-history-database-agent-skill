"""Shared pytest fixtures."""
from __future__ import annotations

from pathlib import Path

import pytest

from indie_match_history import (
    EngineConfig, MatchHistoryEngine, MatchOutcome, MatchResult, Player,
)
from indie_match_history.replay import ReplayStore
from indie_match_history.storage import InMemoryStorage


@pytest.fixture
def memory_engine(tmp_path) -> MatchHistoryEngine:
    cfg = EngineConfig(replay_root=tmp_path / "replays")
    with MatchHistoryEngine(storage=InMemoryStorage(), config=cfg) as eng:
        yield eng


@pytest.fixture
def sqlite_engine(tmp_path: Path) -> MatchHistoryEngine:
    cfg = EngineConfig(sqlite_path=tmp_path / "test.db", replay_root=tmp_path / "replays")
    with MatchHistoryEngine(config=cfg) as eng:
        yield eng


@pytest.fixture(params=["memory_engine", "sqlite_engine"])
def engine(request) -> MatchHistoryEngine:
    return request.getfixturevalue(request.param)


@pytest.fixture
def replay_store(tmp_path: Path) -> ReplayStore:
    return ReplayStore(tmp_path / "replays")


def make_two_players(eng: MatchHistoryEngine, *, minor_b: bool = False):
    a = eng.register_player("alice", region="eu")
    b = eng.register_player("bob", region="na", is_minor=minor_b)
    return a, b


def two_player_match(a: Player, b: Player, a_wins: bool = True):
    return [
        MatchResult(a.player_id, MatchOutcome.WIN if a_wins else MatchOutcome.LOSS),
        MatchResult(b.player_id, MatchOutcome.LOSS if a_wins else MatchOutcome.WIN),
    ]