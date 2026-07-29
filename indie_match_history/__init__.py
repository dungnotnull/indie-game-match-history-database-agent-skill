"""indie_match_history - production-grade match-history database engine for indie games.

Public API surface:
    - Data models:  Player, Match, MatchResult, MatchEvent, ReplayRef, Rating
    - Rating engines: EloEngine, Glicko2Engine
    - Storage: StorageBackend, InMemoryStorage, SQLiteStorage, TieredStorage
    - Leaderboard: Leaderboard (ZSET-style sorted set)
    - Replay blobs: ReplayStore
    - Privacy: PrivacyPipeline, RetentionPolicy
    - Engine facade: MatchHistoryEngine
    - Schema: SCHEMA_VERSION, migrate()
    - Errors: MatchHistoryError and subclasses
"""
from __future__ import annotations

__version__ = "1.1.0"
__all__ = [
    "__version__",
    "errors", "utils", "logging_utils", "config", "schema",
    "models", "ratings", "storage", "leaderboard", "replay",
    "privacy", "engine",
]

from . import errors  # noqa: F401
from . import utils  # noqa: F401
from . import logging_utils  # noqa: F401
from . import config  # noqa: F401
from . import schema  # noqa: F401
from . import models  # noqa: F401
from . import ratings  # noqa: F401
from . import storage  # noqa: F401
from . import leaderboard  # noqa: F401
from . import replay  # noqa: F401
from . import privacy  # noqa: F401
from . import engine  # noqa: F401
from .models import (  # noqa: F401
    Player, Match, MatchResult, MatchEvent, ReplayRef, Rating, MatchOutcome, RatingSystem,
)
from .ratings import EloEngine, Glicko2Engine, RatingEngine  # noqa: F401
from .storage import (  # noqa: F401
    StorageBackend, InMemoryStorage, SQLiteStorage, TieredStorage, StorageTier,
)
from .leaderboard import Leaderboard  # noqa: F401
from .replay import ReplayStore  # noqa: F401
from .privacy import PrivacyPipeline, RetentionPolicy  # noqa: F401
from .engine import MatchHistoryEngine  # noqa: F401
from .schema import SCHEMA_VERSION, migrate  # noqa: F401
from .config import EngineConfig, RetentionConfig, ReplayConfig  # noqa: F401