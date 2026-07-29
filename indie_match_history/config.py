"""Engine configuration dataclasses with safe defaults."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .errors import ConfigurationError


@dataclass(frozen=True)
class RetentionConfig:
    """Retention windows in days. 0 = keep forever (not recommended for PII)."""

    hot_days: int = 30
    warm_days: int = 180
    cold_days: int = 730
    replay_max_age_days: int = 365
    default_gdpr_deletion: bool = True

    def __post_init__(self) -> None:
        for name, value in {
            "hot_days": self.hot_days,
            "warm_days": self.warm_days,
            "cold_days": self.cold_days,
            "replay_max_age_days": self.replay_max_age_days,
        }.items():
            if value < 0:
                raise ConfigurationError(f"{name} must be >= 0, got {value}")
        if not (self.hot_days <= self.warm_days <= self.cold_days):
            raise ConfigurationError(
                "require hot_days <= warm_days <= cold_days"
            )


@dataclass(frozen=True)
class ReplayConfig:
    """Replay blob storage configuration."""

    max_bytes: int = 64 * 1024 * 1024  # 64 MiB ceiling per replay
    gzip_threshold: int = 1024  # compress blobs larger than 1 KiB
    magic: bytes = b"IMHR"  # Indie Match History Replay magic
    dir_name: str = "replays"

    def __post_init__(self) -> None:
        if self.max_bytes <= 0:
            raise ConfigurationError("replay max_bytes must be positive")
        if len(self.magic) < 2:
            raise ConfigurationError("replay magic must be >= 2 bytes")


@dataclass(frozen=True)
class EngineConfig:
    """Top-level engine configuration."""

    rating_system: str = "elo"  # "elo" | "glicko2"
    default_rating: float = 1200.0
    retention: RetentionConfig = field(default_factory=RetentionConfig)
    replay: ReplayConfig = field(default_factory=ReplayConfig)
    sqlite_path: Path | None = None
    replay_root: Path | None = None
    leaderboard_top_default: int = 100
    require_minimum_results: int = 1  # min results to record a match

    def __post_init__(self) -> None:
        if self.rating_system not in ("elo", "glicko2"):
            raise ConfigurationError(
                f"rating_system must be 'elo' or 'glicko2', got {self.rating_system!r}"
            )
        if self.leaderboard_top_default <= 0:
            raise ConfigurationError("leaderboard_top_default must be positive")
        if self.require_minimum_results < 1:
            raise ConfigurationError("require_minimum_results must be >= 1")