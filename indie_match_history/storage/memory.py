"""In-memory storage backend - fast, deterministic, dependency-free.

Suitable for tests, small indie games, and ephemeral sessions. Not durable:
data is lost when the process exits. Thread-safe via a single re-entrant lock.
"""
from __future__ import annotations

import threading
from dataclasses import replace
from typing import Iterable

from ..errors import ConflictError, NotFoundError
from ..models import Match, MatchEvent, MatchResult, Player, Rating, ReplayRef
from .base import PlayerRatingRecord, StorageBackend, StorageTier

_PURGED = "<purged>"


class InMemoryStorage(StorageBackend):
    """Dict-backed storage. O(1) lookups by id; O(n) scans for filters."""

    def __init__(self) -> None:
        self._players: dict[str, Player] = {}
        self._handles: dict[str, str] = {}
        self._matches: dict[str, Match] = {}
        self._events: dict[str, list[MatchEvent]] = {}
        self._ratings: dict[str, list[PlayerRatingRecord]] = {}
        self._replays: dict[str, ReplayRef] = {}
        self._tiers: dict[str, StorageTier] = {}
        self._lock = threading.RLock()

    # -- players -----------------------------------------------------------
    def upsert_player(self, player: Player) -> None:
        with self._lock:
            existing = self._players.get(player.player_id)
            if existing is None and player.handle in self._handles:
                raise ConflictError(f"handle {player.handle!r} already taken")
            self._players[player.player_id] = player
            self._handles[player.handle] = player.player_id

    def get_player(self, player_id: str) -> Player:
        with self._lock:
            player = self._players.get(player_id)
            if player is None:
                raise NotFoundError(f"player {player_id!r} not found")
            return player

    def get_player_by_handle(self, handle: str) -> Player | None:
        with self._lock:
            pid = self._handles.get(handle)
            return self._players.get(pid) if pid else None

    def list_players(self, limit: int = 100, offset: int = 0) -> list[Player]:
        with self._lock:
            players = sorted(self._players.values(), key=lambda p: p.created_at)
            return players[offset: offset + limit]

    def mark_player_deleted(self, player_id: str) -> None:
        with self._lock:
            player = self._players.get(player_id)
            if player is None:
                raise NotFoundError(f"player {player_id!r} not found")
            self._players[player_id] = replace(player, deleted=True)

    # -- matches -----------------------------------------------------------
    def insert_match(self, match: Match) -> None:
        with self._lock:
            if match.match_id in self._matches:
                raise ConflictError(f"match {match.match_id!r} already exists")
            self._matches[match.match_id] = match
            self._tiers[match.match_id] = StorageTier.HOT
            self._events[match.match_id] = list(match.events)

    def get_match(self, match_id: str) -> Match:
        with self._lock:
            m = self._matches.get(match_id)
            if m is None:
                raise NotFoundError(f"match {match_id!r} not found")
            return m

    def list_matches(
        self,
        game_id: str | None = None,
        player_id: str | None = None,
        season: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Match]:
        with self._lock:
            matches = list(self._matches.values())
        if game_id is not None:
            matches = [m for m in matches if m.game_id == game_id]
        if season is not None:
            matches = [m for m in matches if m.season == season]
        if player_id is not None:
            matches = [m for m in matches if player_id in m.participant_ids()]
        matches.sort(key=lambda m: m.started_at, reverse=True)
        return matches[offset: offset + limit]

    def player_history(
        self, player_id: str, limit: int = 100, offset: int = 0
    ) -> list[Match]:
        return self.list_matches(player_id=player_id, limit=limit, offset=offset)

    # -- events ------------------------------------------------------------
    def insert_events(self, events: Iterable[MatchEvent]) -> int:
        events = list(events)
        with self._lock:
            for ev in events:
                if ev.match_id not in self._matches:
                    raise NotFoundError(f"match {ev.match_id!r} not found")
                self._events.setdefault(ev.match_id, []).append(ev)
            return len(events)

    def list_events(self, match_id: str) -> list[MatchEvent]:
        with self._lock:
            if match_id not in self._matches:
                raise NotFoundError(f"match {match_id!r} not found")
            return sorted(self._events.get(match_id, []), key=lambda e: e.ts)

    # -- ratings -----------------------------------------------------------
    def save_rating(self, record: PlayerRatingRecord) -> None:
        with self._lock:
            self._ratings.setdefault(record.player_id, []).append(record)

    def latest_rating(self, player_id: str) -> Rating | None:
        with self._lock:
            hist = self._ratings.get(player_id)
            if not hist:
                return None
            return max(hist, key=lambda r: r.ts).rating

    def rating_history(
        self, player_id: str, limit: int = 100
    ) -> list[PlayerRatingRecord]:
        with self._lock:
            hist = sorted(
                self._ratings.get(player_id, []), key=lambda r: r.ts, reverse=True
            )
            return hist[:limit]

    # -- replays -----------------------------------------------------------
    def upsert_replay(self, replay: ReplayRef) -> None:
        with self._lock:
            self._replays[replay.replay_id] = replay

    def get_replay(self, replay_id: str) -> ReplayRef:
        with self._lock:
            r = self._replays.get(replay_id)
            if r is None:
                raise NotFoundError(f"replay {replay_id!r} not found")
            return r

    def delete_replay(self, replay_id: str) -> None:
        with self._lock:
            if replay_id not in self._replays:
                raise NotFoundError(f"replay {replay_id!r} not found")
            del self._replays[replay_id]

    def link_replay(self, match_id: str, replay_id: str) -> None:
        with self._lock:
            m = self._matches.get(match_id)
            if m is None:
                raise NotFoundError(f"match {match_id!r} not found")
            self._matches[match_id] = replace(m, replay_id=replay_id)

    # -- tiering -----------------------------------------------------------
    def set_match_tier(self, match_id: str, tier: StorageTier) -> None:
        with self._lock:
            if match_id not in self._matches:
                raise NotFoundError(f"match {match_id!r} not found")
            self._tiers[match_id] = tier

    def get_match_tier(self, match_id: str) -> StorageTier:
        with self._lock:
            if match_id not in self._matches:
                raise NotFoundError(f"match {match_id!r} not found")
            return self._tiers.get(match_id, StorageTier.HOT)

    def count_matches(self, game_id: str | None = None) -> int:
        with self._lock:
            if game_id is None:
                return len(self._matches)
            return sum(1 for m in self._matches.values() if m.game_id == game_id)

    # -- privacy -----------------------------------------------------------
    def purge_player_data(self, player_id: str) -> dict[str, int]:
        """GDPR/COPPA purge: anonymize the player and remove 1v1 matches.

        Team matches (>2 participants) are kept but the player's result is
        anonymized to ``<purged>`` so the match record stays intact for the
        other participants while the player's identity is erased.
        """
        summary = {"players": 0, "matches": 0, "events": 0, "ratings": 0, "replays": 0}
        with self._lock:
            player = self._players.get(player_id)
            if player is None:
                raise NotFoundError(f"player {player_id!r} not found")
            handle = player.handle
            self._handles.pop(handle, None)
            del self._players[player_id]
            summary["players"] = 1

            drop_ids: list[str] = []
            for mid, m in list(self._matches.items()):
                participants = m.participant_ids()
                if player_id not in participants:
                    continue
                if len(participants) <= 2:
                    drop_ids.append(mid)
                else:
                    new_results = tuple(
                        replace(
                            r,
                            player_id=_PURGED if r.player_id == player_id else r.player_id,
                            rating_before=None,
                            rating_after=None,
                        )
                        for r in m.results
                    )
                    self._matches[mid] = replace(m, results=new_results)
            for mid in drop_ids:
                summary["events"] += len(self._events.pop(mid, []))
                self._tiers.pop(mid, None)
                del self._matches[mid]
                summary["matches"] += 1
            summary["ratings"] = len(self._ratings.pop(player_id, []))
        return summary