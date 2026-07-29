"""Tiered storage wrapper - records age-based tier transitions.

`TieredStorage` wraps any :class:`StorageBackend` and, based on the engine's
retention windows, recomputes the tier of each match (HOT -> WARM -> COLD ->
ARCHIVED). It does not move bytes itself; tiering metadata drives the privacy
pipeline's eviction and the replay store's compaction. This separation keeps
the storage contract simple while still modelling the indie-game tiering
strategy (hot relational recent rows, warm time-series, cold blob replays).
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Iterable

from ..config import RetentionConfig
from ..errors import NotFoundError
from ..models import Match, MatchEvent, Player, Rating, ReplayRef
from ..utils import utcnow
from .base import PlayerRatingRecord, StorageBackend, StorageTier


class TieredStorage(StorageBackend):
    """Composition wrapper that adds tier-transition bookkeeping."""

    def __init__(self, inner: StorageBackend, retention: RetentionConfig | None = None) -> None:
        self._inner = inner
        self.retention = retention or RetentionConfig()

    @property
    def inner(self) -> StorageBackend:
        return self._inner

    # -- delegation --------------------------------------------------------
    def close(self) -> None:
        self._inner.close()

    def upsert_player(self, player: Player) -> None:
        self._inner.upsert_player(player)

    def get_player(self, player_id: str) -> Player:
        return self._inner.get_player(player_id)

    def get_player_by_handle(self, handle: str) -> Player | None:
        return self._inner.get_player_by_handle(handle)

    def list_players(self, limit: int = 100, offset: int = 0) -> list[Player]:
        return self._inner.list_players(limit=limit, offset=offset)

    def mark_player_deleted(self, player_id: str) -> None:
        self._inner.mark_player_deleted(player_id)

    def insert_match(self, match: Match) -> None:
        self._inner.insert_match(match)

    def get_match(self, match_id: str) -> Match:
        return self._inner.get_match(match_id)

    def list_matches(
        self,
        game_id: str | None = None,
        player_id: str | None = None,
        season: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Match]:
        return self._inner.list_matches(game_id, player_id, season, limit, offset)

    def player_history(
        self, player_id: str, limit: int = 100, offset: int = 0
    ) -> list[Match]:
        return self._inner.player_history(player_id, limit=limit, offset=offset)

    def insert_events(self, events: Iterable[MatchEvent]) -> int:
        return self._inner.insert_events(events)

    def list_events(self, match_id: str) -> list[MatchEvent]:
        return self._inner.list_events(match_id)

    def save_rating(self, record: PlayerRatingRecord) -> None:
        self._inner.save_rating(record)

    def latest_rating(self, player_id: str) -> Rating | None:
        return self._inner.latest_rating(player_id)

    def rating_history(
        self, player_id: str, limit: int = 100
    ) -> list[PlayerRatingRecord]:
        return self._inner.rating_history(player_id, limit=limit)

    def upsert_replay(self, replay: ReplayRef) -> None:
        self._inner.upsert_replay(replay)

    def get_replay(self, replay_id: str) -> ReplayRef:
        return self._inner.get_replay(replay_id)

    def delete_replay(self, replay_id: str) -> None:
        self._inner.delete_replay(replay_id)

    def link_replay(self, match_id: str, replay_id: str) -> None:
        self._inner.link_replay(match_id, replay_id)

    def set_match_tier(self, match_id: str, tier: StorageTier) -> None:
        self._inner.set_match_tier(match_id, tier)

    def get_match_tier(self, match_id: str) -> StorageTier:
        return self._inner.get_match_tier(match_id)

    def count_matches(self, game_id: str | None = None) -> int:
        return self._inner.count_matches(game_id)

    def purge_player_data(self, player_id: str) -> dict[str, int]:
        return self._inner.purge_player_data(player_id)

    # -- tiering logic -----------------------------------------------------
    def tier_for_age(self, age_days: float) -> StorageTier:
        """Map an age (in days) to a storage tier using retention windows."""
        cfg = self.retention
        if age_days <= cfg.hot_days:
            return StorageTier.HOT
        if age_days <= cfg.warm_days:
            return StorageTier.WARM
        if age_days <= cfg.cold_days:
            return StorageTier.COLD
        return StorageTier.ARCHIVED

    def refresh_tier(self, match_id: str, now: datetime | None = None) -> StorageTier:
        """Recompute and persist the tier for a single match based on its age."""
        now = now or utcnow()
        match = self._inner.get_match(match_id)
        age_days = (now - match.started_at).total_seconds() / 86400.0
        tier = self.tier_for_age(age_days)
        self._inner.set_match_tier(match_id, tier)
        return tier

    def refresh_all_tiers(
        self, game_id: str | None = None, now: datetime | None = None
    ) -> dict[str, StorageTier]:
        """Recompute tiers for all (optionally game-scoped) matches.

        Returns a mapping of match_id -> tier. Intended to be called by a
        scheduled job (the privacy pipeline) rather than on every request.
        """
        now = now or utcnow()
        changed: dict[str, StorageTier] = {}
        # Page through all matches; tier refresh is an offline concern.
        offset = 0
        page_size = 500
        while True:
            page = self._inner.list_matches(
                game_id=game_id, limit=page_size, offset=offset
            )
            if not page:
                break
            for m in page:
                age_days = (now - m.started_at).total_seconds() / 86400.0
                tier = self.tier_for_age(age_days)
                if self._inner.get_match_tier(m.match_id) != tier:
                    self._inner.set_match_tier(m.match_id, tier)
                    changed[m.match_id] = tier
            if len(page) < page_size:
                break
            offset += page_size
        return changed