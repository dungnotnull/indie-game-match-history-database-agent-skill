"""Abstract storage backend contract."""
from __future__ import annotations

import enum
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Protocol

from ..models import Match, MatchEvent, MatchResult, Player, Rating, ReplayRef


class StorageTier(str, enum.Enum):
    """Age-based storage tier labels."""

    HOT = "hot"
    WARM = "warm"
    COLD = "cold"
    ARCHIVED = "archived"
    DELETED = "deleted"


@dataclass(frozen=True)
class PlayerRatingRecord:
    """A stored rating snapshot for a player at a point in time."""

    player_id: str
    rating: Rating
    match_id: str | None
    ts: datetime


class StorageBackend(ABC):
    """Abstract storage backend.

    All mutations are explicit; reads return model instances or raise
    :class:`~indie_match_history.errors.NotFoundError`.
    """

    # -- lifecycle ---------------------------------------------------------
    def close(self) -> None:
        """Release any resources. Default no-op."""

    # -- players -----------------------------------------------------------
    @abstractmethod
    def upsert_player(self, player: Player) -> None: ...

    @abstractmethod
    def get_player(self, player_id: str) -> Player: ...

    @abstractmethod
    def get_player_by_handle(self, handle: str) -> Player | None: ...

    @abstractmethod
    def list_players(self, limit: int = 100, offset: int = 0) -> list[Player]: ...

    @abstractmethod
    def mark_player_deleted(self, player_id: str) -> None: ...

    # -- matches -----------------------------------------------------------
    @abstractmethod
    def insert_match(self, match: Match) -> None: ...

    @abstractmethod
    def get_match(self, match_id: str) -> Match: ...

    @abstractmethod
    def list_matches(
        self,
        game_id: str | None = None,
        player_id: str | None = None,
        season: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Match]: ...

    @abstractmethod
    def player_history(
        self, player_id: str, limit: int = 100, offset: int = 0
    ) -> list[Match]: ...

    # -- events ------------------------------------------------------------
    @abstractmethod
    def insert_events(self, events: Iterable[MatchEvent]) -> int: ...

    @abstractmethod
    def list_events(self, match_id: str) -> list[MatchEvent]: ...

    # -- ratings -----------------------------------------------------------
    @abstractmethod
    def save_rating(self, record: PlayerRatingRecord) -> None: ...

    @abstractmethod
    def latest_rating(self, player_id: str) -> Rating | None: ...

    @abstractmethod
    def rating_history(self, player_id: str, limit: int = 100) -> list[PlayerRatingRecord]: ...

    # -- replays -----------------------------------------------------------
    @abstractmethod
    def upsert_replay(self, replay: ReplayRef) -> None: ...

    @abstractmethod
    def get_replay(self, replay_id: str) -> ReplayRef: ...

    @abstractmethod
    def delete_replay(self, replay_id: str) -> None: ...

    @abstractmethod
    def link_replay(self, match_id: str, replay_id: str) -> None:
        """Link a stored replay to an existing (immutable-results) match.

        Match results remain immutable; only the ``replay_id`` reference may be
        set/updated post-creation so replays can be attached asynchronously.
        """
        ...

    # -- tiering -----------------------------------------------------------
    def set_match_tier(self, match_id: str, tier: StorageTier) -> None:
        """Default: no-op; backends that support tiering override this."""
        return None

    @abstractmethod
    def get_match_tier(self, match_id: str) -> StorageTier: ...

    @abstractmethod
    def count_matches(self, game_id: str | None = None) -> int: ...

    # -- privacy helpers ---------------------------------------------------
    @abstractmethod
    def purge_player_data(self, player_id: str) -> dict[str, int]:
        """Hard-delete or anonymize a player's data for GDPR/COPPA.

        Returns a summary of how many records of each kind were affected.
        """
        ...