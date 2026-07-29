"""Production-grade configuration management for indie-game-match-history-database.

This module provides:
- Type-safe configuration classes with validation
- Environment variable handling with sensible defaults
- LLM parameter configuration for skill invocation
- Feature flags for system behavior
- Configuration schema and validation utilities

Configuration hierarchy (highest to lowest priority):
1. Environment variables (INDIE_MATCH_*)
2. .env file in project root
3. Default values in configuration classes
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Literal

from .validation import validate_config, ConfigValidationError
from .schema import get_config_schema, ConfigSchema


__all__ = [
    "validate_config",
    "ConfigValidationError",
    "get_config_schema",
    "ConfigSchema",
    "LLMProvider",
    "LLMConfig",
    "SkillConfig",
    "KnowledgeConfig",
    "FeatureFlags",
    "SystemConfig",
    "get_system_config",
    "reload_config",
]


class LLMProvider(str, Enum):
    """Supported LLM providers for skill execution."""

    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    GOOGLE = "google"
    LOCAL = "local"


@dataclass(frozen=True)
class LLMConfig:
    """LLM parameters for skill invocation and analysis."""

    provider: LLMProvider = LLMProvider.ANTHROPIC
    model: str = "claude-sonnet-4-6"
    temperature: float = 0.7
    max_tokens: int = 8192
    timeout_seconds: int = 120
    max_retries: int = 3
    retry_delay_ms: int = 1000

    def __post_init__(self) -> None:
        if not 0.0 <= self.temperature <= 2.0:
            raise ValueError(f"temperature must be 0-2, got {self.temperature}")
        if self.max_tokens <= 0:
            raise ValueError(f"max_tokens must be positive, got {self.max_tokens}")
        if self.timeout_seconds <= 0:
            raise ValueError(f"timeout_seconds must be positive, got {self.timeout_seconds}")
        if self.max_retries < 0:
            raise ValueError(f"max_retries must be >= 0, got {self.max_retries}")


@dataclass(frozen=True)
class SkillConfig:
    """Configuration for skill behavior and execution."""

    enable_parallel_subskills: bool = True
    max_concurrent_subskills: int = 3
    quality_gate_strict_mode: bool = True
    quality_gate_max_retries: int = 2
    enable_auto_fix: bool = True
    enable_language_detection: bool = True
    default_language: Literal["en", "vi"] = "en"
    fallback_language: Literal["en", "vi"] = "en"

    def __post_init__(self) -> None:
        if self.max_concurrent_subskills <= 0:
            raise ValueError(f"max_concurrent_subskills must be positive, got {self.max_concurrent_subskills}")
        if self.quality_gate_max_retries < 0:
            raise ValueError(f"quality_gate_max_retries must be >= 0, got {self.quality_gate_max_retries}")


@dataclass(frozen=True)
class KnowledgeConfig:
    """Configuration for knowledge crawl pipeline and SECOND-KNOWLEDGE-BRAIN."""

    enable_crawl: bool = True
    crawl_interval_hours: int = 24
    academic_crawl_day: Literal["mon", "tue", "wed", "thu", "fri", "sat", "sun"] = "mon"
    academic_crawl_hour: int = 8
    news_crawl_hour: int = 7
    max_entries_per_crawl: int = 50
    dedup_method: Literal["sha256", "doi", "url"] = "sha256"
    min_score_threshold: float = 3.0
    enable_arxiv: bool = True
    enable_semantic_scholar: bool = True
    enable_rss_feeds: bool = True

    def __post_init__(self) -> None:
        if not 0 <= self.crawl_interval_hours <= 168:
            raise ValueError(f"crawl_interval_hours must be 0-168, got {self.crawl_interval_hours}")
        if not 0 <= self.academic_crawl_hour <= 23:
            raise ValueError(f"academic_crawl_hour must be 0-23, got {self.academic_crawl_hour}")
        if not 0 <= self.news_crawl_hour <= 23:
            raise ValueError(f"news_crawl_hour must be 0-23, got {self.news_crawl_hour}")
        if self.max_entries_per_crawl <= 0:
            raise ValueError(f"max_entries_per_crawl must be positive, got {self.max_entries_per_crawl}")
        if not 0.0 <= self.min_score_threshold <= 10.0:
            raise ValueError(f"min_score_threshold must be 0-10, got {self.min_score_threshold}")


@dataclass(frozen=True)
class FeatureFlags:
    """Feature flags for experimental or optional system behaviors."""

    enable_tiered_storage: bool = True
    enable_replay_compression: bool = True
    enable_gdpr_pipeline: bool = True
    enable_coppa_compliance: bool = True
    enable_leaderboard_caching: bool = True
    enable_schema_migrations: bool = True
    enable_structured_logging: bool = True
    enable_metrics_export: bool = False
    enable_telemetry: bool = False
    enable_experimental_rating_systems: bool = False

    # Advanced features
    enable_query_optimization: bool = True
    enable_bulk_import: bool = True
    enable_anonymization: bool = True


@dataclass(frozen=True)
class LoggingConfig:
    """Configuration for structured logging."""

    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    format: Literal["json", "text"] = "json"
    output_file: str | None = None
    max_file_size_mb: int = 10
    backup_count: int = 5
    enable_console: bool = True
    enable_colored_output: bool = True

    def __post_init__(self) -> None:
        if self.max_file_size_mb <= 0:
            raise ValueError(f"max_file_size_mb must be positive, got {self.max_file_size_mb}")
        if self.backup_count < 0:
            raise ValueError(f"backup_count must be >= 0, got {self.backup_count}")


@dataclass(frozen=True)
class EnginePathsConfig:
    """Paths for engine components and data storage."""

    project_root: Path = field(default_factory=lambda: Path.cwd())
    data_root: Path = field(default_factory=lambda: Path.cwd() / "data")
    database_path: Path = field(default_factory=lambda: Path.cwd() / "data" / "matches.db")
    replay_root: Path = field(default_factory=lambda: Path.cwd() / "data" / "replays")
    log_root: Path = field(default_factory=lambda: Path.cwd() / "logs")
    knowledge_path: Path = field(default_factory=lambda: Path.cwd() / "SECOND-KNOWLEDGE-BRAIN.md"
    )

    def __post_init__(self) -> None:
        # Ensure directory paths are absolute
        object.__setattr__(self, "project_root", self.project_root.resolve())
        object.__setattr__(self, "data_root", self.data_root.resolve())
        object.__setattr__(self, "log_root", self.log_root.resolve())


@dataclass(frozen=True)
class SystemConfig:
    """Top-level system configuration combining all subsystems."""

    llm: LLMConfig = field(default_factory=LLMConfig)
    skill: SkillConfig = field(default_factory=SkillConfig)
    knowledge: KnowledgeConfig = field(default_factory=KnowledgeConfig)
    features: FeatureFlags = field(default_factory=FeatureFlags)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    paths: EnginePathsConfig = field(default_factory=EnginePathsConfig)

    # Version tracking
    config_version: str = "1.0.0"
    environment: Literal["development", "staging", "production"] = "development"


# Global configuration instance
_config_cache: SystemConfig | None = None


def get_system_config(reload: bool = False) -> SystemConfig:
    """Get the current system configuration.

    Args:
        reload: If True, reload configuration from environment and defaults

    Returns:
        The current SystemConfig instance
    """
    global _config_cache

    if _config_cache is None or reload:
        _config_cache = _load_config_from_env()

    return _config_cache


def reload_config() -> SystemConfig:
    """Reload configuration from environment and defaults.

    Returns:
        The reloaded SystemConfig instance
    """
    return get_system_config(reload=True)


def _load_config_from_env() -> SystemConfig:
    """Load configuration from environment variables with fallback to defaults.

    Environment variable prefix: INDIE_MATCH_

    Examples:
        INDIE_MATCH_LLM_PROVIDER=anthropic
        INDIE_MATCH_LLM_MODEL=claude-sonnet-4-6
        INDIE_MATCH_LOG_LEVEL=DEBUG
        INDIE_MATCH_ENABLE_METRICS=true
    """
    env = os.environ

    # Parse LLM config from environment
    provider_str = env.get("INDIE_MATCH_LLM_PROVIDER", "anthropic")
    try:
        llm_provider = LLMProvider(provider_str.lower())
    except ValueError:
        llm_provider = LLMProvider.ANTHROPIC

    llm_config = LLMConfig(
        provider=llm_provider,
        model=env.get("INDIE_MATCH_LLM_MODEL", "claude-sonnet-4-6"),
        temperature=float(env.get("INDIE_MATCH_LLM_TEMPERATURE", "0.7")),
        max_tokens=int(env.get("INDIE_MATCH_LLM_MAX_TOKENS", "8192")),
        timeout_seconds=int(env.get("INDIE_MATCH_LLM_TIMEOUT", "120")),
        max_retries=int(env.get("INDIE_MATCH_LLM_MAX_RETRIES", "3")),
        retry_delay_ms=int(env.get("INDIE_MATCH_LLM_RETRY_DELAY", "1000")),
    )

    # Parse skill config
    skill_config = SkillConfig(
        enable_parallel_subskills=_env_bool("INDIE_MATCH_ENABLE_PARALLEL_SUBSKILLS", True),
        max_concurrent_subskills=int(env.get("INDIE_MATCH_MAX_CONCURRENT_SUBSKILLS", "3")),
        quality_gate_strict_mode=_env_bool("INDIE_MATCH_QUALITY_GATE_STRICT", True),
        quality_gate_max_retries=int(env.get("INDIE_MATCH_QUALITY_GATE_MAX_RETRIES", "2")),
        enable_auto_fix=_env_bool("INDIE_MATCH_ENABLE_AUTO_FIX", True),
        enable_language_detection=_env_bool("INDIE_MATCH_ENABLE_LANGUAGE_DETECTION", True),
        default_language=env.get("INDIE_MATCH_DEFAULT_LANGUAGE", "en"),  # type: ignore
        fallback_language=env.get("INDIE_MATCH_FALLBACK_LANGUAGE", "en"),  # type: ignore
    )

    # Parse knowledge config
    knowledge_config = KnowledgeConfig(
        enable_crawl=_env_bool("INDIE_MATCH_ENABLE_CRAWL", True),
        crawl_interval_hours=int(env.get("INDIE_MATCH_CRAWL_INTERVAL_HOURS", "24")),
        academic_crawl_day=env.get("INDIE_MATCH_ACADEMIC_CRAWL_DAY", "mon"),  # type: ignore
        academic_crawl_hour=int(env.get("INDIE_MATCH_ACADEMIC_CRAWL_HOUR", "8")),
        news_crawl_hour=int(env.get("INDIE_MATCH_NEWS_CRAWL_HOUR", "7")),
        max_entries_per_crawl=int(env.get("INDIE_MATCH_MAX_ENTRIES_PER_CRAWL", "50")),
        dedup_method=env.get("INDIE_MATCH_DEDUP_METHOD", "sha256"),  # type: ignore
        min_score_threshold=float(env.get("INDIE_MATCH_MIN_SCORE_THRESHOLD", "3.0")),
        enable_arxiv=_env_bool("INDIE_MATCH_ENABLE_ARXIV", True),
        enable_semantic_scholar=_env_bool("INDIE_MATCH_ENABLE_SEMANTIC_SCHOLAR", True),
        enable_rss_feeds=_env_bool("INDIE_MATCH_ENABLE_RSS_FEEDS", True),
    )

    # Parse feature flags
    features = FeatureFlags(
        enable_tiered_storage=_env_bool("INDIE_MATCH_ENABLE_TIERED_STORAGE", True),
        enable_replay_compression=_env_bool("INDIE_MATCH_ENABLE_REPLAY_COMPRESSION", True),
        enable_gdpr_pipeline=_env_bool("INDIE_MATCH_ENABLE_GDPR_PIPELINE", True),
        enable_coppa_compliance=_env_bool("INDIE_MATCH_ENABLE_COPPA_COMPLIANCE", True),
        enable_leaderboard_caching=_env_bool("INDIE_MATCH_ENABLE_LEADERBOARD_CACHING", True),
        enable_schema_migrations=_env_bool("INDIE_MATCH_ENABLE_SCHEMA_MIGRATIONS", True),
        enable_structured_logging=_env_bool("INDIE_MATCH_ENABLE_STRUCTURED_LOGGING", True),
        enable_metrics_export=_env_bool("INDIE_MATCH_ENABLE_METRICS_EXPORT", False),
        enable_telemetry=_env_bool("INDIE_MATCH_ENABLE_TELEMETRY", False),
        enable_experimental_rating_systems=_env_bool("INDIE_MATCH_ENABLE_EXPERIMENTAL_RATING", False),
        enable_query_optimization=_env_bool("INDIE_MATCH_ENABLE_QUERY_OPTIMIZATION", True),
        enable_bulk_import=_env_bool("INDIE_MATCH_ENABLE_BULK_IMPORT", True),
        enable_anonymization=_env_bool("INDIE_MATCH_ENABLE_ANONYMIZATION", True),
    )

    # Parse logging config
    logging_config = LoggingConfig(
        level=env.get("INDIE_MATCH_LOG_LEVEL", "INFO"),  # type: ignore
        format=env.get("INDIE_MATCH_LOG_FORMAT", "json"),  # type: ignore
        output_file=env.get("INDIE_MATCH_LOG_FILE"),
        max_file_size_mb=int(env.get("INDIE_MATCH_LOG_MAX_SIZE_MB", "10")),
        backup_count=int(env.get("INDIE_MATCH_LOG_BACKUP_COUNT", "5")),
        enable_console=_env_bool("INDIE_MATCH_LOG_CONSOLE", True),
        enable_colored_output=_env_bool("INDIE_MATCH_LOG_COLORED", True),
    )

    # Parse paths
    project_root = Path(env.get("INDIE_MATCH_PROJECT_ROOT", str(Path.cwd())))

    paths_config = EnginePathsConfig(
        project_root=project_root,
        data_root=Path(env.get("INDIE_MATCH_DATA_ROOT", str(project_root / "data"))),
        database_path=Path(env.get("INDIE_MATCH_DATABASE_PATH", str(project_root / "data" / "matches.db"))),
        replay_root=Path(env.get("INDIE_MATCH_REPLAY_ROOT", str(project_root / "data" / "replays"))),
        log_root=Path(env.get("INDIE_MATCH_LOG_ROOT", str(project_root / "logs"))),
        knowledge_path=Path(env.get("INDIE_MATCH_KNOWLEDGE_PATH", str(project_root / "SECOND-KNOWLEDGE-BRAIN.md"))),
    )

    # Create final config
    return SystemConfig(
        llm=llm_config,
        skill=skill_config,
        knowledge=knowledge_config,
        features=features,
        logging=logging_config,
        paths=paths_config,
        environment=env.get("INDIE_MATCH_ENVIRONMENT", "development"),  # type: ignore
    )


def _env_bool(key: str, default: bool) -> bool:
    """Parse boolean from environment variable.

    Accepts: true, false, 1, 0, yes, no (case-insensitive)
    """
    value = os.environ.get(key, str(default)).lower()
    if value in ("true", "1", "yes", "on"):
        return True
    if value in ("false", "0", "no", "off"):
        return False
    return default
