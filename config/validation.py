"""Configuration validation utilities for indie-game-match-history-database.

Provides validation functions for all configuration classes and
custom validation exceptions.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any


class ConfigValidationError(Exception):
    """Raised when configuration validation fails."""

    def __init__(self, field: str, message: str, value: Any = None) -> None:
        self.field = field
        self.message = message
        self.value = value
        super().__init__(f"Config validation failed for '{field}': {message} (value: {value})")


class ValidationSeverity(str, Enum):
    """Severity levels for validation issues."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass(frozen=True)
class ValidationIssue:
    """A single validation issue found during configuration validation."""

    field: str
    severity: ValidationSeverity
    message: str
    value: Any = None
    suggested_value: Any = None


@dataclass(frozen=True)
class ValidationResult:
    """Result of configuration validation."""

    is_valid: bool
    issues: list[ValidationIssue]
    config_dict: dict[str, Any]

    @property
    def errors(self) -> list[ValidationIssue]:
        """Get only error-level issues."""
        return [i for i in self.issues if i.severity == ValidationSeverity.ERROR]

    @property
    def warnings(self) -> list[ValidationIssue]:
        """Get only warning-level issues."""
        return [i for i in self.issues if i.severity == ValidationSeverity.WARNING]


def validate_config(config: Any) -> ValidationResult:
    """Validate a configuration object and return detailed results.

    Args:
        config: The configuration object to validate (typically SystemConfig)

    Returns:
        ValidationResult with all issues found
    """
    issues: list[ValidationIssue] = []

    # Convert config to dict for easier validation
    config_dict = _config_to_dict(config)

    # Validate LLM configuration
    issues.extend(_validate_llm_config(config_dict.get("llm", {})))

    # Validate skill configuration
    issues.extend(_validate_skill_config(config_dict.get("skill", {})))

    # Validate knowledge configuration
    issues.extend(_validate_knowledge_config(config_dict.get("knowledge", {})))

    # Validate logging configuration
    issues.extend(_validate_logging_config(config_dict.get("logging", {})))

    # Validate paths configuration
    issues.extend(_validate_paths_config(config_dict.get("paths", {})))

    # Validate feature flags
    issues.extend(_validate_feature_flags(config_dict.get("features", {})))

    return ValidationResult(
        is_valid=not any(i.severity == ValidationSeverity.ERROR for i in issues),
        issues=issues,
        config_dict=config_dict,
    )


def _config_to_dict(config: Any) -> dict[str, Any]:
    """Convert a configuration dataclass to a dictionary."""
    if hasattr(config, "__dataclass_fields__"):
        return {
            name: _config_to_dict(getattr(config, name))
            for name in config.__dataclass_fields__
        }
    return config


def _validate_llm_config(llm_config: dict[str, Any]) -> list[ValidationIssue]:
    """Validate LLM configuration."""
    issues: list[ValidationIssue] = []

    # Validate temperature range
    temp = llm_config.get("temperature", 0.7)
    if not 0.0 <= temp <= 2.0:
        issues.append(ValidationIssue(
            field="llm.temperature",
            severity=ValidationSeverity.ERROR,
            message="Temperature must be between 0.0 and 2.0",
            value=temp,
            suggested_value=0.7,
        ))

    # Validate max_tokens
    max_tokens = llm_config.get("max_tokens", 8192)
    if max_tokens <= 0:
        issues.append(ValidationIssue(
            field="llm.max_tokens",
            severity=ValidationSeverity.ERROR,
            message="max_tokens must be positive",
            value=max_tokens,
            suggested_value=8192,
        ))
    elif max_tokens > 200000:
        issues.append(ValidationIssue(
            field="llm.max_tokens",
            severity=ValidationSeverity.WARNING,
            message="max_tokens is very large, may cause slow responses",
            value=max_tokens,
            suggested_value=8192,
        ))

    # Validate timeout
    timeout = llm_config.get("timeout_seconds", 120)
    if timeout <= 0:
        issues.append(ValidationIssue(
            field="llm.timeout_seconds",
            severity=ValidationSeverity.ERROR,
            message="timeout_seconds must be positive",
            value=timeout,
            suggested_value=120,
        ))
    elif timeout < 30:
        issues.append(ValidationIssue(
            field="llm.timeout_seconds",
            severity=ValidationSeverity.WARNING,
            message="timeout_seconds is very short, may cause timeouts for complex queries",
            value=timeout,
            suggested_value=120,
        ))

    return issues


def _validate_skill_config(skill_config: dict[str, Any]) -> list[ValidationIssue]:
    """Validate skill configuration."""
    issues: list[ValidationIssue] = []

    # Validate max_concurrent_subskills
    max_concurrent = skill_config.get("max_concurrent_subskills", 3)
    if max_concurrent <= 0:
        issues.append(ValidationIssue(
            field="skill.max_concurrent_subskills",
            severity=ValidationSeverity.ERROR,
            message="max_concurrent_subskills must be positive",
            value=max_concurrent,
            suggested_value=3,
        ))
    elif max_concurrent > 10:
        issues.append(ValidationIssue(
            field="skill.max_concurrent_subskills",
            severity=ValidationSeverity.WARNING,
            message="max_concurrent_subskills is very large, may cause resource exhaustion",
            value=max_concurrent,
            suggested_value=3,
        ))

    # Validate language settings
    default_lang = skill_config.get("default_language", "en")
    if default_lang not in ("en", "vi"):
        issues.append(ValidationIssue(
            field="skill.default_language",
            severity=ValidationSeverity.WARNING,
            message="default_language should be 'en' or 'vi' for proper translation support",
            value=default_lang,
            suggested_value="en",
        ))

    return issues


def _validate_knowledge_config(knowledge_config: dict[str, Any]) -> list[ValidationIssue]:
    """Validate knowledge configuration."""
    issues: list[ValidationIssue] = []

    # Validate crawl_interval_hours
    interval = knowledge_config.get("crawl_interval_hours", 24)
    if not 0 <= interval <= 168:
        issues.append(ValidationIssue(
            field="knowledge.crawl_interval_hours",
            severity=ValidationSeverity.ERROR,
            message="crawl_interval_hours must be between 0 and 168 (1 week)",
            value=interval,
            suggested_value=24,
        ))

    # Validate min_score_threshold
    min_score = knowledge_config.get("min_score_threshold", 3.0)
    if not 0.0 <= min_score <= 10.0:
        issues.append(ValidationIssue(
            field="knowledge.min_score_threshold",
            severity=ValidationSeverity.ERROR,
            message="min_score_threshold must be between 0.0 and 10.0",
            value=min_score,
            suggested_value=3.0,
        ))

    # Validate crawl hours
    academic_hour = knowledge_config.get("academic_crawl_hour", 8)
    if not 0 <= academic_hour <= 23:
        issues.append(ValidationIssue(
            field="knowledge.academic_crawl_hour",
            severity=ValidationSeverity.ERROR,
            message="academic_crawl_hour must be between 0 and 23",
            value=academic_hour,
            suggested_value=8,
        ))

    news_hour = knowledge_config.get("news_crawl_hour", 7)
    if not 0 <= news_hour <= 23:
        issues.append(ValidationIssue(
            field="knowledge.news_crawl_hour",
            severity=ValidationSeverity.ERROR,
            message="news_crawl_hour must be between 0 and 23",
            value=news_hour,
            suggested_value=7,
        ))

    return issues


def _validate_logging_config(logging_config: dict[str, Any]) -> list[ValidationIssue]:
    """Validate logging configuration."""
    issues: list[ValidationIssue] = []

    # Validate level
    level = logging_config.get("level", "INFO")
    valid_levels = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
    if level not in valid_levels:
        issues.append(ValidationIssue(
            field="logging.level",
            severity=ValidationSeverity.WARNING,
            message=f"log level should be one of {valid_levels}",
            value=level,
            suggested_value="INFO",
        ))

    # Validate format
    log_format = logging_config.get("format", "json")
    if log_format not in ("json", "text"):
        issues.append(ValidationIssue(
            field="logging.format",
            severity=ValidationSeverity.WARNING,
            message="log format should be 'json' or 'text'",
            value=log_format,
            suggested_value="json",
        ))

    return issues


def _validate_paths_config(paths_config: dict[str, Any]) -> list[ValidationIssue]:
    """Validate paths configuration."""
    issues: list[ValidationIssue] = []

    # Check if required paths are strings or Path objects
    path_fields = [
        "project_root",
        "data_root",
        "database_path",
        "replay_root",
        "log_root",
        "knowledge_path",
    ]

    for field in path_fields:
        value = paths_config.get(field)
        if value is None:
            issues.append(ValidationIssue(
                field=f"paths.{field}",
                severity=ValidationSeverity.WARNING,
                message=f"{field} is None, may cause runtime errors",
                value=value,
            ))
        elif not isinstance(value, (str, Path)):
            issues.append(ValidationIssue(
                field=f"paths.{field}",
                severity=ValidationSeverity.ERROR,
                message=f"{field} must be a string or Path object",
                value=value,
            ))

    return issues


def _validate_feature_flags(features_config: dict[str, Any]) -> list[ValidationIssue]:
    """Validate feature flags configuration."""
    issues: list[ValidationIssue] = []

    # Check that all feature flags are boolean
    for key, value in features_config.items():
        if not isinstance(value, bool):
            issues.append(ValidationIssue(
                field=f"features.{key}",
                severity=ValidationSeverity.WARNING,
                message=f"feature flag '{key}' should be boolean, got {type(value).__name__}",
                value=value,
            ))

    return issues


def validate_path_writable(path: Path | str) -> ValidationResult:
    """Validate that a path is writable (or can be created).

    Args:
        path: Path to validate

    Returns:
        ValidationResult with any issues found
    """
    issues: list[ValidationIssue] = []

    try:
        path_obj = Path(path) if isinstance(path, str) else path

        # If path exists, check if it's writable
        if path_obj.exists():
            if not path_obj.is_dir():
                issues.append(ValidationIssue(
                    field="path",
                    severity=ValidationSeverity.ERROR,
                    message=f"Path exists but is not a directory: {path_obj}",
                    value=str(path_obj),
                ))
            elif not os.access(path_obj, os.W_OK):
                issues.append(ValidationIssue(
                    field="path",
                    severity=ValidationSeverity.ERROR,
                    message=f"Path exists but is not writable: {path_obj}",
                    value=str(path_obj),
                ))
        else:
            # Check if parent is writable
            parent = path_obj.parent
            if parent.exists() and not os.access(parent, os.W_OK):
                issues.append(ValidationIssue(
                    field="path",
                    severity=ValidationSeverity.ERROR,
                    message=f"Cannot create path, parent directory is not writable: {parent}",
                    value=str(path_obj),
                ))

    except (OSError, RuntimeError) as e:
        issues.append(ValidationIssue(
            field="path",
            severity=ValidationSeverity.ERROR,
            message=f"Error validating path: {e}",
            value=str(path),
        ))

    return ValidationResult(
        is_valid=not any(i.severity == ValidationSeverity.ERROR for i in issues),
        issues=issues,
        config_dict={"path": str(path)},
    )


def validate_env_var(name: str, required: bool = False) -> ValidationResult:
    """Validate an environment variable.

    Args:
        name: Name of the environment variable
        required: Whether the variable is required

    Returns:
        ValidationResult with any issues found
    """
    import os

    issues: list[ValidationIssue] = []
    value = os.environ.get(name)

    if required and value is None:
        issues.append(ValidationIssue(
            field=f"env.{name}",
            severity=ValidationSeverity.ERROR,
            message=f"Required environment variable '{name}' is not set",
            suggested_value=f"Set {name}=<value>",
        ))
    elif value is not None:
        # Check for empty string
        if not value.strip():
            issues.append(ValidationIssue(
                field=f"env.{name}",
                severity=ValidationSeverity.WARNING,
                message=f"Environment variable '{name}' is set but empty",
                value=value,
            ))

    return ValidationResult(
        is_valid=not any(i.severity == ValidationSeverity.ERROR for i in issues),
        issues=issues,
        config_dict={"env_var": name, "value": value},
    )
