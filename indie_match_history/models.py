"""Typed data models for the match-history engine.

All models are immutable dataclasses that serialize to/from JSON-safe dicts so
any storage backend (in-memory, SQLite JSON columns, future Redis/Postgres) can
round-trip them without bespoke adapters.
"""
from __future__ import annotations

import enum
from dataclasses import asdict, dataclass, field, replace
from datetime import datetime
from typing import Any, Mapping

from .errors import ValidationError
from .utils import isoformat, parse_iso


class MatchOutcome(str, enum.Enum):
    WIN = "win"
    LOSS = "loss"
    DRAW = "draw"
    FORFEIT = "forfeit"

    @classmethod
    def parse(cls, value: str) -> "MatchOutcome":
        try:
            return cls(value.lower())
        except ValueError as exc:
            raise ValidationError(f"invalid outcome {value!r}") from exc


class RatingSystem(str, enum.Enum):
    ELO = "elo"
    GLICKO2 = "glicko2"

    @classmethod
    def parse(cls, value: str) -> "RatingSystem":
        try:
            return cls(value.lower())
        except ValueError as exc:
            raise ValidationError(f"invalid rating system {value!r}") from exc


def _require_nonempty(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{field_name} must be a non-empty string")
    return value


@dataclass(frozen=True)
class Rating:
    """A rating snapshot for a single rating system."""

    value: float
    rd: float = 0.0  # rating deviation (Glicko-2); 0 for ELO
    vol: float = 0.0  # volatility (Glicko-2); 0 for ELO
    system: RatingSystem = RatingSystem.ELO

    def __post_init__(self) -> None:
        if self.system == RatingSystem.GLICKO2:
            if not (0.0 < self.rd):
                raise ValidationError("glicko2 rd must be positive")
            if not (0.0 < self.vol):
                raise ValidationError("glicko2 vol must be positive")
        if self.value < 0:
            raise ValidationError("rating value must be non-negative")

    def to_dict(self) -> dict[str, Any]:
        return {
            "value": self.value,
            "rd": self.rd,
            "vol": self.vol,
            "system": self.system.value,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Rating":
        return cls(
            value=float(data["value"]),
            rd=float(data.get("rd", 0.0)),
            vol=float(data.get("vol", 0.0)),
            system=RatingSystem.parse(str(data.get("system", "elo"))),
        )


@dataclass(frozen=True)
class Player:
    """A player profile. Pseudonymous by design (no real-name PII)."""

    player_id: str
    handle: str
    display_name: str | None = None
    region: str | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    is_minor: bool = False
    deleted: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_nonempty(self.player_id, "player_id")
        _require_nonempty(self.handle, "handle")
        if not isinstance(self.is_minor, bool):
            raise ValidationError("is_minor must be a boolean")

    def to_dict(self) -> dict[str, Any]:
        return {
            "player_id": self.player_id,
            "handle": self.handle,
            "display_name": self.display_name,
            "region": self.region,
            "created_at": isoformat(self.created_at),
            "is_minor": self.is_minor,
            "deleted": self.deleted,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Player":
        return cls(
            player_id=_require_nonempty(str(data["player_id"]), "player_id"),
            handle=_require_nonempty(str(data["handle"]), "handle"),
            display_name=data.get("display_name"),
            region=data.get("region"),
            created_at=parse_iso(str(data["created_at"])),
            is_minor=bool(data.get("is_minor", False)),
            deleted=bool(data.get("deleted", False)),
            metadata=dict(data.get("metadata", {})),
        )

    def redacted(self) -> "Player":
        """Return a pseudonymized copy for public exposure."""
        return replace(self, display_name=None, metadata={})


@dataclass(frozen=True)
class MatchResult:
    """A single player's result within a match."""

    player_id: str
    outcome: MatchOutcome
    team: str | None = None
    score: float | None = None
    rating_before: float | None = None
    rating_after: float | None = None

    def __post_init__(self) -> None:
        _require_nonempty(self.player_id, "player_id")

    @property
    def score_value(self) -> float:
        """Numerical score for ranking: win=1, draw=0.5, loss/forfeit=0."""
        return {
            MatchOutcome.WIN: 1.0,
            MatchOutcome.DRAW: 0.5,
            MatchOutcome.LOSS: 0.0,
            MatchOutcome.FORFEIT: 0.0,
        }[self.outcome]

    def to_dict(self) -> dict[str, Any]:
        return {
            "player_id": self.player_id,
            "outcome": self.outcome.value,
            "team": self.team,
            "score": self.score,
            "rating_before": self.rating_before,
            "rating_after": self.rating_after,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "MatchResult":
        return cls(
            player_id=_require_nonempty(str(data["player_id"]), "player_id"),
            outcome=MatchOutcome.parse(str(data["outcome"])),
            team=data.get("team"),
            score=None if data.get("score") is None else float(data["score"]),
            rating_before=None if data.get("rating_before") is None else float(data["rating_before"]),
            rating_after=None if data.get("rating_after") is None else float(data["rating_after"]),
        )


@dataclass(frozen=True)
class MatchEvent:
    """A discrete in-match event (kill, objective, disconnect, ...)."""

    event_id: str
    match_id: str
    kind: str
    ts: datetime
    player_id: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_nonempty(self.event_id, "event_id")
        _require_nonempty(self.match_id, "match_id")
        _require_nonempty(self.kind, "kind")

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "match_id": self.match_id,
            "kind": self.kind,
            "ts": isoformat(self.ts),
            "player_id": self.player_id,
            "payload": dict(self.payload),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "MatchEvent":
        return cls(
            event_id=_require_nonempty(str(data["event_id"]), "event_id"),
            match_id=_require_nonempty(str(data["match_id"]), "match_id"),
            kind=_require_nonempty(str(data["kind"]), "kind"),
            ts=parse_iso(str(data["ts"])),
            player_id=data.get("player_id"),
            payload=dict(data.get("payload", {})),
        )


@dataclass(frozen=True)
class ReplayRef:
    """Reference to a stored replay blob (the blob itself lives in blob storage)."""

    replay_id: str
    game_id: str
    blob_path: str
    size_bytes: int
    sha256: str
    created_at: datetime
    match_id: str | None = None

    def __post_init__(self) -> None:
        _require_nonempty(self.replay_id, "replay_id")
        _require_nonempty(self.game_id, "game_id")
        _require_nonempty(self.blob_path, "blob_path")
        if self.size_bytes < 0:
            raise ValidationError("size_bytes must be >= 0")
        _require_nonempty(self.sha256, "sha256")

    def to_dict(self) -> dict[str, Any]:
        return {
            "replay_id": self.replay_id,
            "game_id": self.game_id,
            "blob_path": self.blob_path,
            "size_bytes": self.size_bytes,
            "sha256": self.sha256,
            "created_at": isoformat(self.created_at),
            "match_id": self.match_id,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ReplayRef":
        return cls(
            replay_id=_require_nonempty(str(data["replay_id"]), "replay_id"),
            game_id=_require_nonempty(str(data["game_id"]), "game_id"),
            blob_path=_require_nonempty(str(data["blob_path"]), "blob_path"),
            size_bytes=int(data["size_bytes"]),
            sha256=_require_nonempty(str(data["sha256"]), "sha256"),
            created_at=parse_iso(str(data["created_at"])),
            match_id=data.get("match_id"),
        )


@dataclass(frozen=True)
class Match:
    """An immutable match record. Once stored, results may not be edited."""

    match_id: str
    game_id: str
    started_at: datetime
    results: tuple[MatchResult, ...] = ()
    events: tuple[MatchEvent, ...] = ()
    mode: str | None = None
    season: str | None = None
    ended_at: datetime | None = None
    duration_ms: int | None = None
    region: str | None = None
    replay_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_nonempty(self.match_id, "match_id")
        _require_nonempty(self.game_id, "game_id")
        if not self.results:
            raise ValidationError("a match requires at least one result")
        if self.ended_at is not None and self.ended_at < self.started_at:
            raise ValidationError("ended_at cannot precede started_at")
        # Immutability: detect duplicate participants
        participants = [r.player_id for r in self.results]
        if len(participants) != len(set(participants)):
            raise ValidationError("duplicate player in match results")
        if len(self.results) == 2 and not any(
            r.outcome == MatchOutcome.DRAW for r in self.results
        ):
            # A 2-player match must have exactly one winner unless it's a draw.
            winners = sum(1 for r in self.results if r.outcome == MatchOutcome.WIN)
            if winners != 1:
                raise ValidationError(
                    "a 2-player non-draw match must have exactly one winner"
                )

    def to_dict(self) -> dict[str, Any]:
        return {
            "match_id": self.match_id,
            "game_id": self.game_id,
            "started_at": isoformat(self.started_at),
            "results": [r.to_dict() for r in self.results],
            "events": [e.to_dict() for e in self.events],
            "mode": self.mode,
            "season": self.season,
            "ended_at": isoformat(self.ended_at) if self.ended_at else None,
            "duration_ms": self.duration_ms,
            "region": self.region,
            "replay_id": self.replay_id,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Match":
        return cls(
            match_id=_require_nonempty(str(data["match_id"]), "match_id"),
            game_id=_require_nonempty(str(data["game_id"]), "game_id"),
            started_at=parse_iso(str(data["started_at"])),
            results=tuple(MatchResult.from_dict(r) for r in data.get("results", [])),
            events=tuple(MatchEvent.from_dict(e) for e in data.get("events", [])),
            mode=data.get("mode"),
            season=data.get("season"),
            ended_at=parse_iso(str(data["ended_at"])) if data.get("ended_at") else None,
            duration_ms=data.get("duration_ms"),
            region=data.get("region"),
            replay_id=data.get("replay_id"),
            metadata=dict(data.get("metadata", {})),
        )

    def participant_ids(self) -> tuple[str, ...]:
        return tuple(r.player_id for r in self.results)