"""Typed error hierarchy for the match-history engine."""
from __future__ import annotations


class MatchHistoryError(Exception):
    """Base class for all engine errors."""

    code: str = "MATCH_HISTORY_ERROR"


class ValidationError(MatchHistoryError):
    code = "VALIDATION_ERROR"


class NotFoundError(MatchHistoryError):
    code = "NOT_FOUND"


class ConflictError(MatchHistoryError):
    code = "CONFLICT"


class StorageError(MatchHistoryError):
    code = "STORAGE_ERROR"


class SchemaVersionError(MatchHistoryError):
    code = "SCHEMA_VERSION_ERROR"


class PrivacyError(MatchHistoryError):
    code = "PRIVACY_ERROR"


class RatingError(MatchHistoryError):
    code = "RATING_ERROR"


class ReplayError(MatchHistoryError):
    code = "REPLAY_ERROR"


class ConfigurationError(MatchHistoryError):
    code = "CONFIGURATION_ERROR"