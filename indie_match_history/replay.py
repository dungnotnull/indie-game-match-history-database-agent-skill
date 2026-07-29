"""Replay blob storage with optional gzip compression and integrity hashing.

Replays are immutable binary blobs. The store writes them to a content-addressed
layout on disk (``<root>/<sha256[:2]>/<replay_id>.bin``), records a
:class:`~indie_match_history.models.ReplayRef`, and verifies the magic header +
SHA-256 on read-back. This mirrors the cold-blob tier strategy documented in
the skill knowledge base while remaining dependency-free.
"""
from __future__ import annotations

import gzip
import hashlib
import os
from pathlib import Path

from .config import ReplayConfig
from .errors import ConfigurationError, NotFoundError, ReplayError
from .models import ReplayRef
from .utils import isoformat, new_replay_id, utcnow


class ReplayStore:
    """Disk-backed replay blob store with gzip + SHA-256 integrity."""

    def __init__(self, root: str | Path, config: ReplayConfig | None = None) -> None:
        self.config = config or ReplayConfig()
        self.root = Path(root)
        try:
            self.root.mkdir(parents=True, exist_ok=True)
        except OSError as ex:
            raise ConfigurationError(
                f"cannot create replay root {self.root}: {ex}"
            ) from ex

    # -- helpers -----------------------------------------------------------
    def _blob_path(self, replay_id: str, sha256: str) -> Path:
        return self.root / sha256[:2] / f"{replay_id}.bin"

    @staticmethod
    def _sha256(data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    def _maybe_compress(self, data: bytes) -> tuple[bytes, bool]:
        if len(data) >= self.config.gzip_threshold:
            return gzip.compress(data, compresslevel=6), True
        return data, False

    def _maybe_decompress(self, data: bytes) -> bytes:
        # gzip magic: 0x1f 0x8b
        if len(data) >= 2 and data[0] == 0x1F and data[1] == 0x8B:
            try:
                return gzip.decompress(data)
            except OSError as ex:
                raise ReplayError(f"corrupt gzip blob: {ex}") from ex
        return data

    # -- API ---------------------------------------------------------------
    def store(
        self,
        data: bytes,
        game_id: str,
        match_id: str | None = None,
        replay_id: str | None = None,
    ) -> ReplayRef:
        """Validate, persist, and return a :class:`ReplayRef` for ``data``."""
        if not isinstance(data, (bytes, bytearray)):
            raise ReplayError("replay data must be bytes")
        if len(data) == 0:
            raise ReplayError("replay data must be non-empty")
        if len(data) > self.config.max_bytes:
            raise ReplayError(
                f"replay too large: {len(data)} > max {self.config.max_bytes}"
            )
        if not data.startswith(self.config.magic):
            raise ReplayError(
                f"invalid replay magic: expected {self.config.magic!r}"
            )

        replay_id = replay_id or new_replay_id()
        sha256 = self._sha256(bytes(data))
        blob_path = self._blob_path(replay_id, sha256)
        blob_path.parent.mkdir(parents=True, exist_ok=True)

        payload, _compressed = self._maybe_compress(bytes(data))
        # Write atomically: temp file + replace.
        tmp = blob_path.with_suffix(".bin.tmp")
        try:
            with open(tmp, "wb") as fh:
                fh.write(payload)
            os.replace(tmp, blob_path)
        except OSError as ex:
            raise ReplayError(f"failed to write replay blob: {ex}") from ex
        finally:
            if tmp.exists():
                try:
                    tmp.unlink()
                except OSError:
                    pass

        ref = ReplayRef(
            replay_id=replay_id, game_id=game_id, blob_path=str(blob_path),
            size_bytes=len(data), sha256=sha256, created_at=utcnow(),
            match_id=match_id,
        )
        return ref

    def load(self, replay_id: str, expected_sha256: str) -> bytes:
        """Read back a blob and verify its SHA-256 integrity."""
        blob_path = self._blob_path(replay_id, expected_sha256)
        if not blob_path.exists():
            raise NotFoundError(f"replay blob missing at {blob_path}")
        try:
            with open(blob_path, "rb") as fh:
                payload = fh.read()
        except OSError as ex:
            raise ReplayError(f"failed to read replay blob: {ex}") from ex
        data = self._maybe_decompress(payload)
        actual = self._sha256(data)
        if actual != expected_sha256:
            raise ReplayError(
                f"replay sha256 mismatch: expected {expected_sha256}, got {actual}"
            )
        if not data.startswith(self.config.magic):
            raise ReplayError("replay magic missing after decompression")
        return data

    def delete(self, replay_id: str, sha256: str) -> bool:
        blob_path = self._blob_path(replay_id, sha256)
        if not blob_path.exists():
            return False
        try:
            blob_path.unlink()
        except OSError as ex:
            raise ReplayError(f"failed to delete replay blob: {ex}") from ex
        # Clean up empty shard dir.
        try:
            if blob_path.parent.exists() and not any(blob_path.parent.iterdir()):
                blob_path.parent.rmdir()
        except OSError:
            pass
        return True

    def verify(self, replay_ref: ReplayRef) -> bool:
        """Return True iff the on-disk blob hashes to the recorded digest."""
        try:
            data = self.load(replay_ref.replay_id, replay_ref.sha256)
        except (NotFoundError, ReplayError):
            return False
        return len(data) == replay_ref.size_bytes