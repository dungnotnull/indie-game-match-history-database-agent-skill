"""Leaderboard - a Redis ZSET-style sorted set implemented in pure Python.

Operations mirror the Redis sorted-set semantics that competitive games rely on:
  - ZADD with tie-breaking by member id (stable, deterministic ordering)
  - ZRANGE / ZREVRANGE with rank + scores
  - ZINCRBY for rating updates
  - ZSCORE / ZRANK / ZREVRANK
  - ZREMRANGEBYRANK for leaderboard trimming

Tie-break rule (deterministic, reproducible across runs):
  higher score wins; on equal score, lexicographically smaller member id wins.
This guarantees identical leaderboard orderings on every node without
coordinating wall-clock timestamps.
"""
from __future__ import annotations

import bisect
from dataclasses import dataclass
from typing import Iterable, Iterator

from .errors import NotFoundError, ValidationError


@dataclass(frozen=True)
class LeaderboardEntry:
    member: str
    score: float
    rank: int  # 0-indexed rank within the sorted order

    @property
    def position(self) -> int:
        """1-indexed human-friendly rank."""
        return self.rank + 1


def _sort_key(member: str, score: float) -> tuple[float, str]:
    # For descending-by-score / ascending-by-member ordering we store the
    # negated score so bisect on ascending tuples yields the desired order.
    return (-score, member)


class Leaderboard:
    """An ordered, deduplicated mapping of member -> score.

    Not thread-safe by itself; callers (the engine) serialize access.
    """

    def __init__(self, name: str = "default") -> None:
        if not name.strip():
            raise ValidationError("leaderboard name must be non-empty")
        self.name = name
        self._scores: dict[str, float] = {}
        # Parallel sorted list of (neg_score, member) for O(log n) range queries.
        self._sorted: list[tuple[float, str]] = []

    # -- size --------------------------------------------------------------
    def __len__(self) -> int:
        return len(self._scores)

    def __contains__(self, member: str) -> bool:
        return member in self._scores

    def __iter__(self) -> Iterator[str]:
        for _, member in self._sorted:
            yield member

    # -- mutations ---------------------------------------------------------
    def add(self, member: str, score: float) -> bool:
        """ZADD-style set. Returns True if the member is new."""
        self._validate_member(member)
        is_new = member not in self._scores
        if not is_new:
            old = self._scores[member]
            if old == score:
                return False
            self._remove_sorted(member, old)
        self._scores[member] = score
        bisect.insort(self._sorted, _sort_key(member, score))
        return is_new

    def incr_by(self, member: str, delta: float) -> float:
        """ZINCRBY: add delta to the member's score (default 0) and return it."""
        self._validate_member(member)
        new_score = self._scores.get(member, 0.0) + delta
        if member in self._scores:
            self._remove_sorted(member, self._scores[member])
        self._scores[member] = new_score
        bisect.insort(self._sorted, _sort_key(member, new_score))
        return new_score

    def remove(self, member: str) -> bool:
        """ZREM. Returns True if the member was present."""
        if member not in self._scores:
            return False
        self._remove_sorted(member, self._scores[member])
        del self._scores[member]
        return True

    def remove_range_by_rank(self, start: int, stop: int) -> int:
        """ZREMRANGEBYRANK (0-indexed, inclusive). Returns count removed."""
        n = len(self._sorted)
        if n == 0:
            return 0
        lo = max(0, start)
        hi = min(n - 1, stop)
        if lo > hi:
            return 0
        victims = [member for _, member in self._sorted[lo: hi + 1]]
        for member in victims:
            self.remove(member)
        return len(victims)

    def _remove_sorted(self, member: str, score: float) -> None:
        key = _sort_key(member, score)
        idx = bisect.bisect_left(self._sorted, key)
        while idx < len(self._sorted) and self._sorted[idx] == key:
            if self._sorted[idx][1] == member:
                self._sorted.pop(idx)
                return
            idx += 1

    @staticmethod
    def _validate_member(member: str) -> None:
        if not isinstance(member, str) or not member.strip():
            raise ValidationError("leaderboard member must be a non-empty string")

    # -- queries -----------------------------------------------------------
    def score(self, member: str) -> float:
        if member not in self._scores:
            raise NotFoundError(f"member {member!r} not in leaderboard {self.name!r}")
        return self._scores[member]

    def rank(self, member: str) -> int:
        """0-indexed rank (top of board = 0)."""
        if member not in self._scores:
            raise NotFoundError(f"member {member!r} not in leaderboard {self.name!r}")
        key = _sort_key(member, self._scores[member])
        idx = bisect.bisect_left(self._sorted, key)
        while idx < len(self._sorted) and self._sorted[idx] == key:
            if self._sorted[idx][1] == member:
                return idx
            idx += 1
        raise NotFoundError(f"member {member!r} not in leaderboard {self.name!r}")

    def rev_rank(self, member: str) -> int:
        return self.rank(member)

    def around(self, member: str, window: int = 2) -> list[LeaderboardEntry]:
        """Return up to 2*window+1 entries centred on ``member``."""
        center = self.rank(member)
        lo = max(0, center - window)
        hi = min(len(self._sorted) - 1, center + window)
        return self.range(lo, hi)

    def range(self, start: int, stop: int) -> list[LeaderboardEntry]:
        """ZRANGE-style slice (0-indexed, inclusive) in descending score order."""
        lo = max(0, start)
        hi = min(len(self._sorted) - 1, stop)
        if lo > hi:
            return []
        return [
            LeaderboardEntry(member=member, score=-neg, rank=idx)
            for idx, (neg, member) in enumerate(self._sorted[lo: hi + 1], start=lo)
        ]

    def top(self, n: int = 10) -> list[LeaderboardEntry]:
        if n <= 0:
            return []
        return self.range(0, n - 1)

    def bottom(self, n: int = 10) -> list[LeaderboardEntry]:
        if n <= 0:
            return []
        size = len(self._sorted)
        return self.range(size - n, size - 1)

    # -- bulk --------------------------------------------------------------
    def bulk_add(self, items: Iterable[tuple[str, float]]) -> int:
        count = 0
        for member, score in items:
            self.add(member, score)
            count += 1
        return count

    def to_dict(self) -> dict[str, float]:
        return dict(self._scores)

    @classmethod
    def from_dict(cls, name: str, data: dict[str, float]) -> "Leaderboard":
        lb = cls(name=name)
        for member, score in data.items():
            lb.add(member, float(score))
        return lb