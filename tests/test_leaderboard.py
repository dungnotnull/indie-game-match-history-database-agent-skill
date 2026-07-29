"""Tests for the ZSET-style leaderboard."""
from __future__ import annotations

import pytest

from indie_match_history import Leaderboard
from indie_match_history.errors import NotFoundError, ValidationError


def test_add_and_top_ordering():
    lb = Leaderboard("s1")
    lb.add("a", 1200)
    lb.add("b", 1500)
    lb.add("c", 1500)
    top = lb.top(3)
    assert [e.member for e in top] == ["b", "c", "a"]  # b<c on tie by id
    assert top[0].position == 1


def test_incr_by():
    lb = Leaderboard("s1")
    lb.add("a", 1000)
    assert lb.incr_by("a", 50) == 1050
    assert lb.score("a") == 1050


def test_remove_and_membership():
    lb = Leaderboard("s1")
    lb.add("a", 100)
    assert "a" in lb
    assert lb.remove("a") is True
    assert "a" not in lb
    assert lb.remove("a") is False


def test_rank_and_rev_rank():
    lb = Leaderboard("s1")
    for m, s in [("a", 1000), ("b", 1500), ("c", 1200)]:
        lb.add(m, s)
    assert lb.rank("b") == 0
    assert lb.rank("a") == 2
    assert lb.rev_rank("c") == 1


def test_around():
    lb = Leaderboard("s1")
    for i, m in enumerate(["a", "b", "c", "d", "e"]):
        lb.add(m, 1000 - i)
    around = lb.around("c", window=1)
    assert [e.member for e in around] == ["b", "c", "d"]


def test_remove_range_by_rank():
    lb = Leaderboard("s1")
    for i, m in enumerate(["a", "b", "c", "d", "e"]):
        lb.add(m, 1000 - i)
    removed = lb.remove_range_by_rank(3, 4)  # drop d,e (bottom)
    assert removed == 2
    assert [e.member for e in lb.top(5)] == ["a", "b", "c"]


def test_missing_member_raises():
    lb = Leaderboard("s1")
    with pytest.raises(NotFoundError):
        lb.score("ghost")
    with pytest.raises(NotFoundError):
        lb.rank("ghost")


def test_invalid_member_rejected():
    lb = Leaderboard("s1")
    with pytest.raises(ValidationError):
        lb.add("", 100)
    with pytest.raises(ValidationError):
        Leaderboard("")


def test_from_to_dict_roundtrip():
    lb = Leaderboard("s1")
    lb.bulk_add([("a", 1.0), ("b", 2.0)])
    data = lb.to_dict()
    lb2 = Leaderboard.from_dict("s1", data)
    assert lb2.score("a") == 1.0
    assert lb2.score("b") == 2.0


def test_update_same_score_noop():
    lb = Leaderboard("s1")
    assert lb.add("a", 100) is True   # new
    assert lb.add("a", 100) is False  # same score, no change