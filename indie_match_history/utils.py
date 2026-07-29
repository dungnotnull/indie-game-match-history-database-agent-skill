"""Internal utilities: identifiers, timestamps, hashing."""
from __future__ import annotations

import hashlib
import secrets
import time
import uuid
from datetime import datetime, timezone


def utcnow() -> datetime:
    """Timezone-aware UTC now."""
    return datetime.now(timezone.utc)


def epoch_ns(dt: datetime | None = None) -> int:
    """Convert a datetime to nanoseconds since the Unix epoch."""
    dt = dt or utcnow()
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1_000_000_000)


def new_player_id() -> str:
    """Generate a sortable, collision-resistant player id (ULID-like)."""
    ts = int(time.time() * 1000)
    rand = secrets.token_hex(8)
    return f"pl_{ts:013d}{rand}"


def new_match_id() -> str:
    """Generate a sortable match id."""
    ts = int(time.time() * 1000)
    rand = secrets.token_hex(8)
    return f"mt_{ts:013d}{rand}"


def new_replay_id() -> str:
    return f"rp_{uuid.uuid4().hex}"


def stable_hash(*parts: str) -> str:
    """SHA-256 of joined lowercased parts (used for dedup)."""
    joined = "|".join(p.strip().lower() for p in parts if p).encode("utf-8")
    return hashlib.sha256(joined).hexdigest()


def isoformat(dt: datetime) -> str:
    """ISO-8601 UTC string with Z suffix."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    dt = dt.astimezone(timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.") + f"{dt.microsecond:06d}Z"


def parse_iso(value: str) -> datetime:
    """Parse an ISO-8601 timestamp robustly, returning tz-aware UTC."""
    s = value.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def clamp(value: float, lo: float, hi: float) -> float:
    if value < lo:
        return lo
    if value > hi:
        return hi
    return value