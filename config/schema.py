"""Configuration schema definitions and JSON schema export.

Provides schema definitions for all configuration classes and utilities
for generating JSON schemas for documentation and validation.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any


class ConfigFormat(str, Enum):
    """Supported configuration export formats."""

    JSON = "json"
    YAML = "yaml"
    TOML = "toml"
    ENV = "env"


@dataclass(frozen=True)
class ConfigFieldDef:
    """Definition of a single configuration field."""

    name: str
    type: str
    description: str
    default: Any = None
    required: bool = True
    env_var: str | None = None
    choices: list[Any] | None = None
    range: tuple[Any, Any] | None = None
    validation: str | None = None


@dataclass(frozen=True)
class ConfigSchema:
    """Schema definition for a configuration class."""

    name: str
    description: str
    version: str
    fields: list[ConfigFieldDef]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_json_schema(self) -> dict[str, Any]:
        """Convert to JSON Schema format."""
        properties = {}
        required_fields = []

        for field_def in self.fields:
            prop_schema = {
                "description": field_def.description,
                "type": _map_type_to_json_type(field_def.type),
            }

            if field_def.default is not None:
                prop_schema["default"] = field_def.default

            if field_def.choices:
                prop_schema["enum"] = field_def.choices

            if field_def.range:
                prop_schema["minimum"] = field_def.range[0]
                prop_schema["maximum"] = field_def.range[1]

            if field_def.env_var:
                prop_schema["env_var"] = field_def.env_var

            if field_def.validation:
                prop_schema["validation"] = field_def.validation

            properties[field_def.name] = prop_schema

            if field_def.required:
                required_fields.append(field_def.name)

        return {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "title": self.name,
            "description": self.description,
            "type": "object",
            "properties": properties,
            "required": required_fields,
            "additionalProperties": False,
            "metadata": {
                "version": self.version,
                "generated_at": datetime.now().isoformat(),
                **self.metadata,
            },
        }

    def export(self, path: Path | str, format: ConfigFormat = ConfigFormat.JSON) -> None:
        """Export schema to a file.

        Args:
            path: Output file path
            format: Export format (json, yaml, toml, env)
        """
        path_obj = Path(path) if isinstance(path, str) else path
        path_obj.parent.mkdir(parents=True, exist_ok=True)

        if format == ConfigFormat.JSON:
            with path_obj.open("w", encoding="utf-8") as f:
                json.dump(self.to_json_schema(), f, indent=2)
        elif format == ConfigFormat.YAML:
            try:
                import yaml
                with path_obj.open("w", encoding="utf-8") as f:
                    yaml.dump(self.to_json_schema(), f, default_flow_style=False)
            except ImportError:
                raise ImportError("PyYAML is required for YAML export")
        elif format == ConfigFormat.TOML:
            try:
                import tomli_w
                # Convert to a format suitable for TOML
                toml_data = _json_schema_to_toml(self.to_json_schema())
                with path_obj.open("wb") as f:
                    tomli_w.dump(toml_data, f)
            except ImportError:
                raise ImportError("tomli_w is required for TOML export")
        elif format == ConfigFormat.ENV:
            self._export_env(path_obj)
        else:
            raise ValueError(f"Unsupported format: {format}")

    def _export_env(self, path: Path) -> None:
        """Export as .env file template."""
        with path.open("w", encoding="utf-8") as f:
            f.write(f"# {self.name} Configuration\n")
            f.write(f"# Generated: {datetime.now().isoformat()}\n")
            f.write(f"# Version: {self.version}\n\n")

            for field_def in self.fields:
                f.write(f"# {field_def.description}\n")
                if field_def.choices:
                    f.write(f"# Choices: {', '.join(map(str, field_def.choices))}\n")
                if field_def.range:
                    f.write(f"# Range: {field_def.range[0]} - {field_def.range[1]}\n")

                env_var = field_def.env_var or f"INDIE_MATCH_{field_def.name.upper()}"
                default = field_def.default if field_def.default is not None else ""

                f.write(f"{env_var}={default}\n\n")


def _map_type_to_json_type(python_type: str) -> str | list[str]:
    """Map Python type string to JSON Schema type."""
    type_map = {
        "str": "string",
        "int": "integer",
        "float": "number",
        "bool": "boolean",
        "list": "array",
        "dict": "object",
        "Path": "string",
    }

    # Handle union types (e.g., "str | None")
    if "|" in python_type or "Literal[" in python_type:
        # Try to extract the base types
        base_types = []
        for t in ("str", "int", "float", "bool"):
            if t in python_type:
                base_types.append(type_map.get(t, "string"))
        return base_types if base_types else ["string", "null"]

    return type_map.get(python_type, "string")


def _json_schema_to_toml(schema: dict[str, Any]) -> dict[str, Any]:
    """Convert JSON Schema to a format suitable for TOML export."""
    # TOML doesn't support all JSON Schema features, so simplify
    toml_data = {
        "schema": schema.get("title", ""),
        "description": schema.get("description", ""),
        "version": schema.get("metadata", {}).get("version", "1.0.0"),
    }

    properties = schema.get("properties", {})
    for key, value in properties.items():
        # Simplify the property schema for TOML
        toml_data[key] = {
            "description": value.get("description", ""),
            "type": value.get("type", "string"),
        }

        if "default" in value:
            toml_data[key]["default"] = value["default"]
        if "enum" in value:
            toml_data[key]["choices"] = value["enum"]
        if "env_var" in value:
            toml_data[key]["env_var"] = value["env_var"]

    return toml_data


# Define schemas for all configuration classes
def get_llm_config_schema() -> ConfigSchema:
    """Get schema for LLMConfig."""
    return ConfigSchema(
        name="LLMConfig",
        description="Configuration for LLM parameters used in skill invocation",
        version="1.0.0",
        fields=[
            ConfigFieldDef(
                name="provider",
                type="LLMProvider",
                description="LLM provider to use for skill execution",
                default="anthropic",
                choices=["anthropic", "openai", "google", "local"],
                env_var="INDIE_MATCH_LLM_PROVIDER",
            ),
            ConfigFieldDef(
                name="model",
                type="str",
                description="Model name to use",
                default="claude-sonnet-4-6",
                env_var="INDIE_MATCH_LLM_MODEL",
            ),
            ConfigFieldDef(
                name="temperature",
                type="float",
                description="Sampling temperature (0.0-2.0)",
                default=0.7,
                range=(0.0, 2.0),
                env_var="INDIE_MATCH_LLM_TEMPERATURE",
            ),
            ConfigFieldDef(
                name="max_tokens",
                type="int",
                description="Maximum tokens per response",
                default=8192,
                range=(1, 200000),
                env_var="INDIE_MATCH_LLM_MAX_TOKENS",
            ),
            ConfigFieldDef(
                name="timeout_seconds",
                type="int",
                description="Request timeout in seconds",
                default=120,
                range=(1, 600),
                env_var="INDIE_MATCH_LLM_TIMEOUT",
            ),
            ConfigFieldDef(
                name="max_retries",
                type="int",
                description="Maximum retry attempts",
                default=3,
                range=(0, 10),
                env_var="INDIE_MATCH_LLM_MAX_RETRIES",
            ),
            ConfigFieldDef(
                name="retry_delay_ms",
                type="int",
                description="Delay between retries in milliseconds",
                default=1000,
                range=(0, 10000),
                env_var="INDIE_MATCH_LLM_RETRY_DELAY",
            ),
        ],
    )


def get_skill_config_schema() -> ConfigSchema:
    """Get schema for SkillConfig."""
    return ConfigSchema(
        name="SkillConfig",
        description="Configuration for skill behavior and execution",
        version="1.0.0",
        fields=[
            ConfigFieldDef(
                name="enable_parallel_subskills",
                type="bool",
                description="Enable parallel execution of sub-skills",
                default=True,
                env_var="INDIE_MATCH_ENABLE_PARALLEL_SUBSKILLS",
            ),
            ConfigFieldDef(
                name="max_concurrent_subskills",
                type="int",
                description="Maximum number of sub-skills to run concurrently",
                default=3,
                range=(1, 10),
                env_var="INDIE_MATCH_MAX_CONCURRENT_SUBSKILLS",
            ),
            ConfigFieldDef(
                name="quality_gate_strict_mode",
                type="bool",
                description="Enable strict quality gate enforcement",
                default=True,
                env_var="INDIE_MATCH_QUALITY_GATE_STRICT",
            ),
            ConfigFieldDef(
                name="quality_gate_max_retries",
                type="int",
                description="Maximum quality gate retry attempts",
                default=2,
                range=(0, 5),
                env_var="INDIE_MATCH_QUALITY_GATE_MAX_RETRIES",
            ),
            ConfigFieldDef(
                name="enable_auto_fix",
                type="bool",
                description="Enable automatic fixing of quality gate failures",
                default=True,
                env_var="INDIE_MATCH_ENABLE_AUTO_FIX",
            ),
            ConfigFieldDef(
                name="enable_language_detection",
                type="bool",
                description="Enable automatic language detection",
                default=True,
                env_var="INDIE_MATCH_ENABLE_LANGUAGE_DETECTION",
            ),
            ConfigFieldDef(
                name="default_language",
                type="str",
                description="Default language for output",
                default="en",
                choices=["en", "vi"],
                env_var="INDIE_MATCH_DEFAULT_LANGUAGE",
            ),
            ConfigFieldDef(
                name="fallback_language",
                type="str",
                description="Fallback language if detection fails",
                default="en",
                choices=["en", "vi"],
                env_var="INDIE_MATCH_FALLBACK_LANGUAGE",
            ),
        ],
    )


def get_knowledge_config_schema() -> ConfigSchema:
    """Get schema for KnowledgeConfig."""
    return ConfigSchema(
        name="KnowledgeConfig",
        description="Configuration for knowledge crawl pipeline",
        version="1.0.0",
        fields=[
            ConfigFieldDef(
                name="enable_crawl",
                type="bool",
                description="Enable automated knowledge crawling",
                default=True,
                env_var="INDIE_MATCH_ENABLE_CRAWL",
            ),
            ConfigFieldDef(
                name="crawl_interval_hours",
                type="int",
                description="Hours between crawl runs",
                default=24,
                range=(0, 168),
                env_var="INDIE_MATCH_CRAWL_INTERVAL_HOURS",
            ),
            ConfigFieldDef(
                name="academic_crawl_day",
                type="str",
                description="Day of week for academic crawl",
                default="mon",
                choices=["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
                env_var="INDIE_MATCH_ACADEMIC_CRAWL_DAY",
            ),
            ConfigFieldDef(
                name="academic_crawl_hour",
                type="int",
                description="Hour of day for academic crawl (0-23)",
                default=8,
                range=(0, 23),
                env_var="INDIE_MATCH_ACADEMIC_CRAWL_HOUR",
            ),
            ConfigFieldDef(
                name="news_crawl_hour",
                type="int",
                description="Hour of day for news crawl (0-23)",
                default=7,
                range=(0, 23),
                env_var="INDIE_MATCH_NEWS_CRAWL_HOUR",
            ),
            ConfigFieldDef(
                name="max_entries_per_crawl",
                type="int",
                description="Maximum entries to fetch per crawl",
                default=50,
                range=(1, 1000),
                env_var="INDIE_MATCH_MAX_ENTRIES_PER_CRAWL",
            ),
            ConfigFieldDef(
                name="dedup_method",
                type="str",
                description="Deduplication method",
                default="sha256",
                choices=["sha256", "doi", "url"],
                env_var="INDIE_MATCH_DEDUP_METHOD",
            ),
            ConfigFieldDef(
                name="min_score_threshold",
                type="float",
                description="Minimum score for entries to be included",
                default=3.0,
                range=(0.0, 10.0),
                env_var="INDIE_MATCH_MIN_SCORE_THRESHOLD",
            ),
            ConfigFieldDef(
                name="enable_arxiv",
                type="bool",
                description="Enable ArXiv crawling",
                default=True,
                env_var="INDIE_MATCH_ENABLE_ARXIV",
            ),
            ConfigFieldDef(
                name="enable_semantic_scholar",
                type="bool",
                description="Enable Semantic Scholar crawling",
                default=True,
                env_var="INDIE_MATCH_ENABLE_SEMANTIC_SCHOLAR",
            ),
            ConfigFieldDef(
                name="enable_rss_feeds",
                type="bool",
                description="Enable RSS feed crawling",
                default=True,
                env_var="INDIE_MATCH_ENABLE_RSS_FEEDS",
            ),
        ],
    )


def get_feature_flags_schema() -> ConfigSchema:
    """Get schema for FeatureFlags."""
    return ConfigSchema(
        name="FeatureFlags",
        description="Feature flags for system behaviors",
        version="1.0.0",
        fields=[
            ConfigFieldDef(
                name="enable_tiered_storage",
                type="bool",
                description="Enable tiered hot/warm/cold storage",
                default=True,
                env_var="INDIE_MATCH_ENABLE_TIERED_STORAGE",
            ),
            ConfigFieldDef(
                name="enable_replay_compression",
                type="bool",
                description="Enable replay blob compression",
                default=True,
                env_var="INDIE_MATCH_ENABLE_REPLAY_COMPRESSION",
            ),
            ConfigFieldDef(
                name="enable_gdpr_pipeline",
                type="bool",
                description="Enable GDPR compliance pipeline",
                default=True,
                env_var="INDIE_MATCH_ENABLE_GDPR_PIPELINE",
            ),
            ConfigFieldDef(
                name="enable_coppa_compliance",
                type="bool",
                description="Enable COPPA compliance for minors",
                default=True,
                env_var="INDIE_MATCH_ENABLE_COPPA_COMPLIANCE",
            ),
            ConfigFieldDef(
                name="enable_leaderboard_caching",
                type="bool",
                description="Enable leaderboard result caching",
                default=True,
                env_var="INDIE_MATCH_ENABLE_LEADERBOARD_CACHING",
            ),
            ConfigFieldDef(
                name="enable_schema_migrations",
                type="bool",
                description="Enable automatic schema migrations",
                default=True,
                env_var="INDIE_MATCH_ENABLE_SCHEMA_MIGRATIONS",
            ),
            ConfigFieldDef(
                name="enable_structured_logging",
                type="bool",
                description="Enable structured JSON logging",
                default=True,
                env_var="INDIE_MATCH_ENABLE_STRUCTURED_LOGGING",
            ),
            ConfigFieldDef(
                name="enable_metrics_export",
                type="bool",
                description="Enable metrics export (OpenTelemetry)",
                default=False,
                env_var="INDIE_MATCH_ENABLE_METRICS_EXPORT",
            ),
            ConfigFieldDef(
                name="enable_telemetry",
                type="bool",
                description="Enable anonymous telemetry",
                default=False,
                env_var="INDIE_MATCH_ENABLE_TELEMETRY",
            ),
            ConfigFieldDef(
                name="enable_experimental_rating_systems",
                type="bool",
                description="Enable experimental rating systems",
                default=False,
                env_var="INDIE_MATCH_ENABLE_EXPERIMENTAL_RATING",
            ),
        ],
    )


def get_logging_config_schema() -> ConfigSchema:
    """Get schema for LoggingConfig."""
    return ConfigSchema(
        name="LoggingConfig",
        description="Configuration for structured logging",
        version="1.0.0",
        fields=[
            ConfigFieldDef(
                name="level",
                type="str",
                description="Log level",
                default="INFO",
                choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                env_var="INDIE_MATCH_LOG_LEVEL",
            ),
            ConfigFieldDef(
                name="format",
                type="str",
                description="Log output format",
                default="json",
                choices=["json", "text"],
                env_var="INDIE_MATCH_LOG_FORMAT",
            ),
            ConfigFieldDef(
                name="output_file",
                type="str | None",
                description="Log file output path (None for stdout)",
                default=None,
                required=False,
                env_var="INDIE_MATCH_LOG_FILE",
            ),
            ConfigFieldDef(
                name="max_file_size_mb",
                type="int",
                description="Maximum log file size before rotation",
                default=10,
                range=(1, 1000),
                env_var="INDIE_MATCH_LOG_MAX_SIZE_MB",
            ),
            ConfigFieldDef(
                name="backup_count",
                type="int",
                description="Number of backup logs to keep",
                default=5,
                range=(0, 100),
                env_var="INDIE_MATCH_LOG_BACKUP_COUNT",
            ),
            ConfigFieldDef(
                name="enable_console",
                type="bool",
                description="Enable console output",
                default=True,
                env_var="INDIE_MATCH_LOG_CONSOLE",
            ),
            ConfigFieldDef(
                name="enable_colored_output",
                type="bool",
                description="Enable colored console output",
                default=True,
                env_var="INDIE_MATCH_LOG_COLORED",
            ),
        ],
    )


def get_system_config_schema() -> ConfigSchema:
    """Get complete system configuration schema."""
    return ConfigSchema(
        name="SystemConfig",
        description="Complete system configuration for indie-game-match-history-database",
        version="1.0.0",
        metadata={
            "project": "indie-game-match-history-database",
            "version": "1.1.0",
            "env_prefix": "INDIE_MATCH_",
        },
        fields=[
            # Combine all sub-config fields
            *get_llm_config_schema().fields,
            *get_skill_config_schema().fields,
            *get_knowledge_config_schema().fields,
            *get_feature_flags_schema().fields,
            *get_logging_config_schema().fields,
            ConfigFieldDef(
                name="config_version",
                type="str",
                description="Configuration schema version",
                default="1.0.0",
            ),
            ConfigFieldDef(
                name="environment",
                type="str",
                description="Deployment environment",
                default="development",
                choices=["development", "staging", "production"],
                env_var="INDIE_MATCH_ENVIRONMENT",
            ),
        ],
    )


def get_config_schema(config_type: str = "system") -> ConfigSchema:
    """Get configuration schema by type.

    Args:
        config_type: Type of schema ("system", "llm", "skill", "knowledge",
                      "features", "logging")

    Returns:
        ConfigSchema for the requested type
    """
    schemas = {
        "system": get_system_config_schema,
        "llm": get_llm_config_schema,
        "skill": get_skill_config_schema,
        "knowledge": get_knowledge_config_schema,
        "features": get_feature_flags_schema,
        "logging": get_logging_config_schema,
    }

    if config_type not in schemas:
        raise ValueError(f"Unknown config type: {config_type}. Available: {list(schemas.keys())}")

    return schemas[config_type]()


def export_all_schemas(output_dir: Path | str) -> None:
    """Export all configuration schemas to JSON files.

    Args:
        output_dir: Directory to write schema files
    """
    output_path = Path(output_dir) if isinstance(output_dir, str) else output_dir
    output_path.mkdir(parents=True, exist_ok=True)

    for config_type in ["system", "llm", "skill", "knowledge", "features", "logging"]:
        schema = get_config_schema(config_type)
        file_path = output_path / f"{config_type}_config_schema.json"
        schema.export(file_path, ConfigFormat.JSON)
