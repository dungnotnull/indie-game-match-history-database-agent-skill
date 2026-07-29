"""Storage backends for the match-history engine.

Backends implement :class:`StorageBackend`. Two concrete backends ship:
  - :class:`InMemoryStorage` - fast, deterministic, for tests and small games.
  - :class:`SQLiteStorage` - durable, file-based default for indie deployments.
  - :class:`TieredStorage` - composes a primary backend with age-based tiering
    metadata so hot/warm/cold eviction can be driven by the privacy pipeline.
"""
from __future__ import annotations

from .base import StorageBackend, StorageTier
from .memory import InMemoryStorage
from .sqlite import SQLiteStorage
from .tiered import TieredStorage

__all__ = [
    "StorageBackend", "StorageTier",
    "InMemoryStorage", "SQLiteStorage", "TieredStorage",
]