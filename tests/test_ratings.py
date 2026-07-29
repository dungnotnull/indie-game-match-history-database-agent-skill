"""Tests for ELO and Glicko-2 rating engines."""
from __future__ import annotations

import pytest

from indie_match_history import (
    EloEngine, Glicko2Engine, MatchOutcome, Rating, RatingSystem,
)
from indie_match_history.errors import RatingError
from indie_match_history.ratings import make_engine


def test_elo_expected_score_bounds():
    elo = EloEngine()
    assert elo.expected(1400, 1400) == 0.5
    assert elo.expected(2000, 1000) > 0.99
    assert elo.expected(1000, 2000) < 0.01


def test_elo_winner_gains_loser_drops():
    elo = EloEngine()
    a, b = Rating(value=1500.0), Rating(value=1500.0)
    a_new = elo.update(a, [(b, MatchOutcome.WIN)])
    b_new = elo.update(b, [(a, MatchOutcome.LOSS)])
    assert a_new.value > a.value
    assert b_new.value < b.value
    assert abs((a_new.value + b_new.value) - (a.value + b.value)) < 0.01


def test_elo_k_ladder():
    elo = EloEngine()
    assert elo._k_for(Rating(value=1000.0)) == elo.k_provisional
    assert elo._k_for(Rating(value=2300.0)) == elo.k_mid
    assert elo._k_for(Rating(value=2500.0)) == elo.k_top


def test_elo_requires_opponent():
    with pytest.raises(RatingError):
        EloEngine().update(Rating(1500.0), [])


def test_elo_forfeit_treated_as_loss():
    elo = EloEngine()
    a, b = Rating(value=1500.0), Rating(value=1500.0)
    a_new = elo.update(a, [(b, MatchOutcome.FORFEIT)])
    assert a_new.value < a.value


def test_glicko2_winner_up_loser_down():
    g = Glicko2Engine()
    a, b = g.default_rating(), g.default_rating()
    a_new = g.update(a, [(b, MatchOutcome.WIN)])
    b_new = g.update(b, [(a, MatchOutcome.LOSS)])
    assert a_new.value > a.value
    assert b_new.value < b.value
    assert a_new.system == RatingSystem.GLICKO2
    assert a_new.rd > 0 and a_new.vol > 0


def test_glicko2_rd_shrinks_with_games():
    g = Glicko2Engine()
    a, b = g.default_rating(), g.default_rating()
    cur = a
    for _ in range(5):
        cur = g.update(cur, [(b, MatchOutcome.WIN)])
    assert cur.rd < a.rd


def test_glicko2_requires_opponent():
    with pytest.raises(RatingError):
        Glicko2Engine().update(Glicko2Engine().default_rating(), [])


def test_make_engine_factory():
    assert make_engine("elo").system == RatingSystem.ELO
    assert make_engine("glicko2").system == RatingSystem.GLICKO2