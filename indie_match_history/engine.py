"""MatchHistoryEngine - the high-level facade that wires every component.

The engine is the single integration point indie game servers should use. It
composes a storage backend, a rating engine, a leaderboard registry, an optional
replay store, and a privacy pipeline, exposing ergonomic, transactional-style
operations:

  - register_player / get_player
  - record_match (validates, persists the immutable match, recomputes ratings
    for every participant, persists rating snapshots, and updates leaderboards)
  - attach_replay (stores a blob + links it to a match)
  - leaderboard(game_id, season)
  - player_history / player_rating_history
  - run_retention / erase_player

All public methods are thread-safe via the storage backend's lock and the
engine's own leaderboard lock.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Iterable, Mapping

from .config import EngineConfig
from .errors import (
    ConfigurationError, NotFoundError, ValidationError, RatingError,
)
from .leaderboard import Leaderboard
from .logging_utils import get_logger
from .models import (
    Match, MatchEvent, MatchOutcome, MatchResult, Player, Rating, RatingSystem, ReplayRef,
)
from .privacy import PrivacyPipeline, RetentionPolicy
from .ratings import EloEngine, Glicko2Engine, RatingEngine, make_engine
from .replay import ReplayStore
from .storage.base import PlayerRatingRecord, StorageBackend, StorageTier
from .storage.memory import InMemoryStorage
from .storage.sqlite import SQLiteStorage
from .storage.tiered import TieredStorage
from .utils import new_match_id, new_player_id, utcnow
from . import __version__ as _VERSION

_log = get_logger("engine")


@dataclass(frozen=True)
class RecordMatchResult:
    """Outcome summary of :meth:`MatchHistoryEngine.record_match`."""

    match: Match
    rating_deltas: dict[str, tuple[float, float]]  # player_id -> (before, after)
    leaderboard_updates: dict[str, float]  # member -> new score


class MatchHistoryEngine:
    """The orchestrating facade for the match-history database engine."""

    def __init__(
        self,
        storage: StorageBackend | None = None,
        config: EngineConfig | None = None,
        replay_store: ReplayStore | None = None,
        rating_engine: RatingEngine | None = None,
    ) -> None:
        self.config = config or EngineConfig()
        cfg = self.config

        replay_store = replay_store or (
            ReplayStore(cfg.replay_root, cfg.replay) if cfg.replay_root else None
        )

        if storage is None:
            if cfg.sqlite_path is not None:
                storage = SQLiteStorage(cfg.sqlite_path)
            else:
                storage = InMemoryStorage()

        # Wrap primary storage in tiering unless it is already tiered.
        if isinstance(storage, TieredStorage):
            self.storage: StorageBackend = storage
            self.tiered = storage
        else:
            self.tiered = TieredStorage(storage, cfg.retention)
            self.storage = self.tiered

        self.replay_store = replay_store
        self.rating_engine: RatingEngine = rating_engine or make_engine(cfg.rating_system)
        # Validate that the configured rating system matches the engine's.
        if self.rating_engine.system != RatingSystem.parse(cfg.rating_system):
            raise ConfigurationError(
                "rating_engine system does not match config.rating_system"
            )
        self.privacy = PrivacyPipeline(
            self.storage, replay_store=replay_store,
            policy=RetentionPolicy(config=cfg.retention),
        )
        self._leaderboards: dict[str, Leaderboard] = {}
        self._lb_lock = threading.RLock()

    # -- lifecycle ---------------------------------------------------------
    def close(self) -> None:
        self.storage.close()

    def __enter__(self) -> "MatchHistoryEngine":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    # -- players -----------------------------------------------------------
    def register_player(
        self,
        handle: str,
        *,
        display_name: str | None = None,
        region: str | None = None,
        is_minor: bool = False,
        player_id: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> Player:
        """Create a pseudonymous player and seed their initial rating."""
        if not handle.strip():
            raise ValidationError("handle must be non-empty")
        player = Player(
            player_id=player_id or new_player_id(),
            handle=handle.strip(),
            display_name=display_name,
            region=region,
            created_at=utcnow(),
            is_minor=is_minor,
            metadata=dict(metadata or {}),
        )
        self.storage.upsert_player(player)
        # Seed initial rating snapshot (no associated match).
        self.storage.save_rating(
            PlayerRatingRecord(
                player_id=player.player_id,
                rating=self.rating_engine.default_rating(),
                match_id=None,
                ts=utcnow(),
            )
        )
        _log.info("player registered", extra={"player_id": player.player_id})
        return player

    def get_player(self, player_id: str) -> Player:
        return self.storage.get_player(player_id)

    def get_player_by_handle(self, handle: str) -> Player | None:
        return self.storage.get_player_by_handle(handle)

    def player_rating(self, player_id: str) -> Rating:
        rating = self.storage.latest_rating(player_id)
        if rating is None:
            raise NotFoundError(f"no rating for player {player_id!r}")
        return rating

    def player_rating_history(self, player_id: str, limit: int = 100):
        return self.storage.rating_history(player_id, limit=limit)

    # -- matches -----------------------------------------------------------
    def record_match(
        self,
        game_id: str,
        results: Iterable[MatchResult | Mapping[str, Any]],
        *,
        mode: str | None = None,
        season: str | None = None,
        started_at: datetime | None = None,
        ended_at: datetime | None = None,
        duration_ms: int | None = None,
        region: str | None = None,
        events: Iterable[MatchEvent] | None = None,
        metadata: Mapping[str, Any] | None = None,
        match_id: str | None = None,
    ) -> RecordMatchResult:
        """Validate, persist, rate, and leaderboard-update a match atomically.

        Rating recomputation uses each participant's latest stored rating as the
        "before" state, applies the engine over their opponents' latest ratings,
        and persists the "after" snapshot. Leaderboards are keyed by
        ``(game_id, season)``. Casual matches (``mode == 'casual'``) skip BOTH
        rating recomputation and leaderboard updates to keep ranked pools clean.
        """
        if not game_id.strip():
            raise ValidationError("game_id must be non-empty")
        parsed_results = self._coerce_results(results)
        if len(parsed_results) < self.config.require_minimum_results:
            raise ValidationError(
                f"match requires at least {self.config.require_minimum_results} result(s)"
            )

        started_at = started_at or utcnow()
        match = Match(
            match_id=match_id or new_match_id(),
            game_id=game_id,
            started_at=started_at,
            results=tuple(parsed_results),
            events=tuple(events or ()),
            mode=mode, season=season, ended_at=ended_at,
            duration_ms=duration_ms, region=region,
            metadata=dict(metadata or {}),
        )

        # Verify all participants exist (and are not deleted).
        for pid in match.participant_ids():
            try:
                p = self.storage.get_player(pid)
            except NotFoundError as ex:
                raise NotFoundError(f"participant {pid!r} not registered") from ex
            if p.deleted:
                raise ValidationError(f"participant {pid!r} is deleted")

        # Rating recomputation (skip for casual mode).
        deltas: dict[str, tuple[float, float]] = {}
        if mode != "casual":
            for r in parsed_results:
                before = self.storage.latest_rating(r.player_id)
                if before is None:
                    before = self.rating_engine.default_rating()
                opponents = self._opponent_pairs(r.player_id, parsed_results)
                after = self.rating_engine.update(before, opponents)
                deltas[r.player_id] = (before.value, after.value)
                self.storage.save_rating(
                    PlayerRatingRecord(
                        player_id=r.player_id, rating=after,
                        match_id=match.match_id, ts=utcnow(),
                    )
                )
            # Stamp before/after onto the result objects we persist.
            parsed_results = tuple(
                MatchResult(
                    player_id=r.player_id, outcome=r.outcome, team=r.team,
                    score=r.score,
                    rating_before=deltas[r.player_id][0] if r.player_id in deltas else None,
                    rating_after=deltas[r.player_id][1] if r.player_id in deltas else None,
                )
                for r in parsed_results
            )
            match = Match(
                match_id=match.match_id, game_id=match.game_id,
                started_at=match.started_at, results=parsed_results,
                events=match.events, mode=match.mode, season=match.season,
                ended_at=match.ended_at, duration_ms=match.duration_ms,
                region=match.region, replay_id=match.replay_id,
                metadata=match.metadata,
            )

        # Persist the (immutable) match.
        self.storage.insert_match(match)

        # Leaderboard updates (ranked only).
        lb_updates: dict[str, float] = {}
        if mode != "casual" and season is not None:
            lb = self._leaderboard(game_id, season)
            for pid, (_, after) in deltas.items():
                lb.add(pid, after)
                lb_updates[pid] = after

        _log.info(
            "match recorded",
            extra={"match_id": match.match_id, "game_id": game_id,
                   "participants": len(parsed_results)},
        )
        return RecordMatchResult(match=match, rating_deltas=deltas,
                                  leaderboard_updates=lb_updates)

    @staticmethod
    def _coerce_results(
        results: Iterable[MatchResult | Mapping[str, Any]],
    ) -> list[MatchResult]:
        out: list[MatchResult] = []
        for r in results:
            if isinstance(r, MatchResult):
                out.append(r)
            elif isinstance(r, Mapping):
                out.append(MatchResult.from_dict(r))
            else:
                raise ValidationError(
                    f"result must be MatchResult or mapping, got {type(r).__name__}"
                )
        return out

    def _opponent_pairs(
        self, player_id: str, results: list[MatchResult]
    ) -> list[tuple[Rating, MatchOutcome]]:
        """Build the (opponent_rating, outcome) pairs for one participant.

        In a 1v1 match the single opponent is paired with this player's outcome.
        In a multi-player free-for-all we conservatively treat every other
        participant as an opponent with this player's outcome vs an implicit
        "the field" - to avoid overstating signal, we instead only pair against
        opponents whose outcome is the inverse (winners vs losers). For draws
        we pair each opponent with a draw. This keeps FFA updates well-defined
        without inventing a custom FFA formula.
        """
        me = next(r for r in results if r.player_id == player_id)
        pairs: list[tuple[Rating, MatchOutcome]] = []
        for r in results:
            if r.player_id == player_id:
                continue
            opp_rating = self.storage.latest_rating(r.player_id)
            if opp_rating is None:
                opp_rating = self.rating_engine.default_rating()
            # Derive my outcome vs this opponent from a 1v1 lens.
            if me.outcome == MatchOutcome.DRAW:
                my_outcome = MatchOutcome.DRAW
            elif me.outcome == r.outcome:
                my_outcome = MatchOutcome.DRAW  # same standing -> draw lens
            elif me.outcome == MatchOutcome.WIN and r.outcome in (
                MatchOutcome.LOSS, MatchOutcome.FORFEIT
            ):
                my_outcome = MatchOutcome.WIN
            elif me.outcome in (MatchOutcome.LOSS, MatchOutcome.FORFEIT) and r.outcome == MatchOutcome.WIN:
                my_outcome = MatchOutcome.LOSS
            else:
                my_outcome = MatchOutcome.DRAW
            pairs.append((opp_rating, my_outcome))
        if not pairs:
            raise RatingError("no opponents found for rating update")
        return pairs

    # -- queries -----------------------------------------------------------
    def get_match(self, match_id: str) -> Match:
        return self.storage.get_match(match_id)

    def player_history(self, player_id: str, limit: int = 100, offset: int = 0):
        return self.storage.player_history(player_id, limit=limit, offset=offset)

    def list_matches(self, game_id: str | None = None, season: str | None = None,
                     limit: int = 100, offset: int = 0):
        return self.storage.list_matches(game_id=game_id, season=season,
                                          limit=limit, offset=offset)

    def leaderboard(self, game_id: str, season: str, top: int | None = None) -> list:
        lb = self._leaderboard(game_id, season)
        n = top if top is not None else self.config.leaderboard_top_default
        return lb.top(n)

    def leaderboard_around(self, game_id: str, season: str, player_id: str,
                           window: int = 2):
        lb = self._leaderboard(game_id, season)
        if player_id not in lb:
            # Rebuild from stored ratings if the in-memory board was lost.
            self._rebuild_leaderboard(game_id, season, lb)
        if player_id not in lb:
            raise NotFoundError(f"player {player_id!r} not on leaderboard")
        return lb.around(player_id, window=window)

    def _leaderboard(self, game_id: str, season: str) -> Leaderboard:
        key = f"{game_id}|{season}"
        with self._lb_lock:
            lb = self._leaderboards.get(key)
            if lb is None:
                lb = Leaderboard(name=key)
                self._rebuild_leaderboard(game_id, season, lb)
                self._leaderboards[key] = lb
            return lb

    def _rebuild_leaderboard(self, game_id: str, season: str, lb: Leaderboard) -> None:
        """Repopulate ``lb`` from the latest rating of each ranked participant."""
        matches = self.storage.list_matches(game_id=game_id, season=season, limit=10_000)
        seen: set[str] = set()
        # Walk newest-first; a player's most recent match carries their latest
        # rating for this season.
        for m in matches:
            if m.mode == "casual":
                continue
            for r in m.results:
                if r.player_id in seen or r.player_id == "<purged>":
                    continue
                if r.rating_after is not None:
                    lb.add(r.player_id, r.rating_after)
                    seen.add(r.player_id)

    # -- replays -----------------------------------------------------------
    def attach_replay(
        self, match_id: str, data: bytes, *, replay_id: str | None = None,
    ) -> ReplayRef:
        if self.replay_store is None:
            raise ConfigurationError("no replay store configured")
        match = self.storage.get_match(match_id)
        ref = self.replay_store.store(
            data, game_id=match.game_id, match_id=match.match_id, replay_id=replay_id,
        )
        self.storage.upsert_replay(ref)
        # Link the replay back onto the match so retention/queries can find it.
        # Match results stay immutable; only the replay reference is updated.
        self.storage.link_replay(match.match_id, ref.replay_id)
        _log.info("replay attached", extra={"match_id": match_id, "replay_id": ref.replay_id})
        return ref

    def load_replay(self, replay_id: str) -> bytes:
        if self.replay_store is None:
            raise ConfigurationError("no replay store configured")
        ref = self.storage.get_replay(replay_id)
        return self.replay_store.load(ref.replay_id, ref.sha256)

    # -- privacy / retention ----------------------------------------------
    def run_retention(self, now: datetime | None = None, game_id: str | None = None):
        return self.privacy.run_retention(now=now, game_id=game_id)

    def erase_player(self, player_id: str) -> dict[str, int]:
        # Drop from in-memory leaderboards too.
        with self._lb_lock:
            for lb in self._leaderboards.values():
                lb.remove(player_id)
        return self.privacy.erase_player(player_id)

    # -- diagnostics -------------------------------------------------------
    def stats(self) -> dict[str, Any]:
        return {
            "version": _VERSION,
            "rating_system": self.config.rating_system,
            "matches": self.storage.count_matches(),
            "players": len(self.storage.list_players(limit=10_000_000)),
            "leaderboards": len(self._leaderboards),
            "replay_store": self.replay_store is not None,
        }