"""Tests for typed data models and serialization round-trips."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from indie_match_history import (
    Match, MatchEvent, MatchOutcome, MatchResult, Player, Rating, RatingSystem,
)
from indie_match_history.errors import ValidationError


def test_player_roundtrip():
    p = Player(player_id="pl_1", handle="alice", region="eu",
               created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
               is_minor=False, metadata={"k": "v"})
    p2 = Player.from_dict(p.to_dict())
    assert p2 == p


def test_player_redacted_drops_pii():
    p = Player(player_id="pl_1", handle="alice", display_name="Alice Real",
               metadata={"email": "x@y"})
    r = p.redacted()
    assert r.display_name is None and r.metadata == {}
    assert r.handle == "alice"


def test_player_invalid_raises():
    with pytest.raises(ValidationError):
        Player(player_id="", handle="alice")
    with pytest.raises(ValidationError):
        Player(player_id="pl_1", handle="")


def test_rating_glicko_requires_positive_rd_vol():
    with pytest.raises(ValidationError):
        Rating(value=1500, rd=0.0, vol=0.06, system=RatingSystem.GLICKO2)


def test_rating_roundtrip():
    r = Rating(value=1234.5, rd=50.0, vol=0.06, system=RatingSystem.GLICKO2)
    assert Rating.from_dict(r.to_dict()) == r


def test_match_requires_results():
    with pytest.raises(ValidationError):
        Match(match_id="m1", game_id="pong", started_at=datetime.now(timezone.utc))


def test_match_two_player_winner_constraint():
    ts = datetime.now(timezone.utc)
    with pytest.raises(ValidationError):
        Match(match_id="m1", game_id="pong", started_at=ts,
              results=(MatchResult("pl_a", MatchOutcome.LOSS),
                       MatchResult("pl_b", MatchOutcome.LOSS)))


def test_match_duplicate_participant_rejected():
    ts = datetime.now(timezone.utc)
    with pytest.raises(ValidationError):
        Match(match_id="m1", game_id="pong", started_at=ts,
              results=(MatchResult("pl_a", MatchOutcome.WIN),
                       MatchResult("pl_a", MatchOutcome.LOSS)))


def test_match_roundtrip_with_events():
    ts = datetime.now(timezone.utc)
    ev = MatchEvent(event_id="e1", match_id="m1", kind="kill", ts=ts,
                    player_id="pl_a", payload={"weapon": "sword"})
    m = Match(match_id="m1", game_id="pong", started_at=ts, season="s1",
              results=(MatchResult("pl_a", MatchOutcome.WIN),
                       MatchResult("pl_b", MatchOutcome.LOSS)),
              events=(ev,), duration_ms=1200)
    m2 = Match.from_dict(m.to_dict())
    assert m2 == m
    assert m2.participant_ids() == ("pl_a", "pl_b")


def test_match_outcome_parse_invalid():
    with pytest.raises(ValidationError):
        MatchOutcome.parse("nonsense")


def test_match_ended_before_started_rejected():
    ts = datetime.now(timezone.utc)
    with pytest.raises(ValidationError):
        Match(match_id="m1", game_id="pong", started_at=ts,
              ended_at=ts.replace(year=2020),
              results=(MatchResult("pl_a", MatchOutcome.WIN),
                       MatchResult("pl_b", MatchOutcome.LOSS)))