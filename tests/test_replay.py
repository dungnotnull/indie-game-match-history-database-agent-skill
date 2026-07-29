"""Tests for the replay blob store."""
from __future__ import annotations

import hashlib

import pytest

from indie_match_history import ReplayConfig, ReplayRef, ReplayStore
from indie_match_history.errors import NotFoundError, ReplayError
from indie_match_history.utils import utcnow


def _blob(cfg: ReplayConfig, body: bytes = b"frame-data" * 50) -> bytes:
    return cfg.magic + body


def test_store_load_roundtrip(replay_store: ReplayStore):
    cfg = replay_store.config
    blob = _blob(cfg)
    ref = replay_store.store(blob, game_id="pong", match_id="m1")
    assert ref.size_bytes == len(blob)
    assert replay_store.verify(ref) is True
    assert replay_store.load(ref.replay_id, ref.sha256) == blob


def test_store_compresses_large_blob(replay_store: ReplayStore):
    cfg = replay_store.config
    blob = _blob(cfg, body=b"\x00" * (cfg.gzip_threshold + 4096))
    ref = replay_store.store(blob, game_id="pong")
    # The on-disk file should be smaller than the raw blob for compressible data.
    from pathlib import Path
    on_disk = Path(ref.blob_path).stat().st_size
    assert on_disk < len(blob)


def test_rejects_bad_magic(replay_store: ReplayStore):
    with pytest.raises(ReplayError):
        replay_store.store(b"BAD_MAGIC" + b"x" * 100, game_id="pong")


def test_rejects_empty(replay_store: ReplayStore):
    with pytest.raises(ReplayError):
        replay_store.store(b"", game_id="pong")


def test_rejects_too_large(replay_store: ReplayStore, tmp_path):
    cfg = ReplayConfig(max_bytes=64, gzip_threshold=1024 * 1024)
    store = ReplayStore(tmp_path / "rp", config=cfg)
    with pytest.raises(ReplayError):
        store.store(cfg.magic + b"x" * 100, game_id="pong")


def test_load_missing_raises(replay_store: ReplayStore):
    with pytest.raises(NotFoundError):
        replay_store.load("rp_ghost", "0" * 64)


def test_corrupt_blob_detected(replay_store: ReplayStore):
    cfg = replay_store.config
    blob = _blob(cfg)
    ref = replay_store.store(blob, game_id="pong")
    from pathlib import Path
    p = Path(ref.blob_path)
    # Truncate the on-disk blob to corrupt it (bypass compression for tiny blob).
    p.write_bytes(cfg.magic + b"tampered")
    with pytest.raises(ReplayError):
        replay_store.load(ref.replay_id, ref.sha256)


def test_delete(replay_store: ReplayStore):
    cfg = replay_store.config
    ref = replay_store.store(_blob(cfg), game_id="pong")
    assert replay_store.delete(ref.replay_id, ref.sha256) is True
    assert replay_store.delete(ref.replay_id, ref.sha256) is False
    assert replay_store.verify(ref) is False