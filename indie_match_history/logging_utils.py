"""Structured logging setup for the engine."""
from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any

_LOGGER_NAME = "indie_match_history"


class _JsonFormatter(logging.Formatter):
    """Minimal JSON line formatter (no external deps)."""

    _RESERVED = {
        "args", "msg", "levelname", "name", "filename", "module",
        "exc_info", "exc_text", "stack_info", "lineno", "funcName",
        "created", "msecs", "relativeCreated", "thread", "threadName",
        "processName", "process", "pathname", "levelno", "message",
    }

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.")
            + f"{record.msecs:06.0f}Z",
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        for key, val in record.__dict__.items():
            if key in payload or key.startswith("_") or key in self._RESERVED:
                continue
            try:
                json.dumps(val)
                payload[key] = val
            except (TypeError, ValueError):
                payload[key] = repr(val)
        return json.dumps(payload, ensure_ascii=False)


def get_logger(name: str | None = None) -> logging.Logger:
    """Return the configured logger; idempotent."""
    base = logging.getLogger(_LOGGER_NAME)
    if not base.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(_JsonFormatter())
        base.addHandler(handler)
        base.setLevel(logging.INFO)
        base.propagate = False
    if name is None or name == _LOGGER_NAME:
        return base
    return base.getChild(name)