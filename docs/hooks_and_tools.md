# Hooks & Tools System Design

## Overview

The indie-game-match-history-database harness uses a lightweight hooks and tools system to manage lifecycle events, state synchronization, and tool execution. This document formalizes the design and implementation of these systems.

## Hooks System

### Hook Definition

A **hook** is a lifecycle event point where custom code can be executed to extend or modify the harness behavior.

### Hook Types

#### 1. Lifecycle Hooks

| Hook Name | Trigger | Purpose | Parameters |
|------------|---------|---------|-------------|
| `pre_harness` | Before harness execution | Setup, validation | `config: SystemConfig` |
| `post_harness` | After harness execution | Cleanup, logging | `result: dict` |
| `pre_step_N` | Before step N (1-5) | Step preparation | `step_name: str, context: dict` |
| `post_step_N` | After step N (1-5) | Step processing | `step_name: str, result: dict` |
| `pre_quality_gate` | Before quality gate review | Gate preparation | `output: dict` |
| `post_quality_gate` | After quality gate review | Gate processing | `result: dict` |
| `on_degradation` | On degradation level change | Degradation handling | `level: DegradationLevel` |
| `on_error` | On error occurrence | Error handling | `error: Exception, context: dict` |

#### 2. Synchronization Hooks

| Hook Name | Trigger | Purpose | Parameters |
|------------|---------|---------|-------------|
| `state_sync` | On state change | State synchronization | `old_state: dict, new_state: dict` |
| `config_update` | On configuration change | Config reload | `old_config: SystemConfig, new_config: SystemConfig` |
| `knowledge_update` | On knowledge base update | Knowledge refresh | `entries: list[Candidate]` |

#### 3. Emission Hooks

| Hook Name | Trigger | Purpose | Parameters |
|------------|---------|---------|-------------|
| `emit_metric` | On metric generation | Metrics export | `metric: str, value: float, tags: dict` |
| `emit_log` | On log event | Structured logging | `level: str, message: str, context: dict` |
| `emit_event` | On significant event | Event tracking | `event_type: str, payload: dict` |

### Hook Implementation

The hooks system is implemented as a simple event emitter:

```python
from typing import Callable, Any
from dataclasses import dataclass
from enum import Enum

class HookName(str, Enum):
    """Named hooks in the harness."""
    PRE_HARNESS = "pre_harness"
    POST_HARNESS = "post_harness"
    PRE_STEP_1 = "pre_step_1"
    POST_STEP_1 = "post_step_1"
    # ... etc for all steps
    PRE_QUALITY_GATE = "pre_quality_gate"
    POST_QUALITY_GATE = "post_quality_gate"
    ON_DEGRADATION = "on_degradation"
    ON_ERROR = "on_error"

@dataclass
class HookContext:
    """Context passed to hook handlers."""
    hook_name: HookName
    parameters: dict[str, Any]
    config: SystemConfig

class HookHandler:
    """Hook registry and executor."""

    def __init__(self) -> None:
        self._hooks: dict[HookName, list[Callable]] = {}

    def register(self, hook_name: HookName, handler: Callable) -> None:
        """Register a handler for a hook."""
        if hook_name not in self._hooks:
            self._hooks[hook_name] = []
        self._hooks[hook_name].append(handler)

    def emit(self, hook_name: HookName, context: HookContext) -> None:
        """Execute all handlers for a hook."""
        for handler in self._hooks.get(hook_name, []):
            try:
                handler(context)
            except Exception as e:
                _log.error(f"Hook {hook_name} handler failed", exc_info=e)
```

### Hook Usage Example

```python
# Register a pre-harness hook
hook_handler.register(
    HookName.PRE_HARNESS,
    lambda ctx: validate_config(ctx.config)
)

# Register a metric emission hook
hook_handler.register(
    HookName.EMIT_METRIC,
    lambda ctx: export_to_prometheus(ctx.parameters)
)
```

### Built-in Hook Handlers

#### Pre-Harness Validation

```python
def pre_harness_validation(context: HookContext) -> None:
    """Validate configuration and dependencies before harness execution."""
    from .validation import validate_config

    result = validate_config(context.config)
    if not result.is_valid:
        raise ConfigurationError(
            f"Configuration validation failed: {result.errors}"
        )
```

#### Post-Step Logging

```python
def post_step_logging(context: HookContext) -> None:
    """Log step completion with metrics."""
    step_name = context.parameters.get("step_name")
    result = context.parameters.get("result")

    _log.info(
        "Step completed",
        step=step_name,
        duration_ms=result.get("duration_ms"),
        success=result.get("success", True),
    )
```

#### Degradation Notification

```python
def on_degradation_handler(context: HookContext) -> None:
    """Handle degradation level changes."""
    level = context.parameters.get("level")

    _log.warning(
        "Degradation level changed",
        level=level.value,
        limitation=get_limitation_message(level),
    )

    # Emit metric
    hook_handler.emit(
        HookName.EMIT_METRIC,
        HookContext(
            hook_name=HookName.EMIT_METRIC,
            parameters={
                "metric": "degradation_level",
                "value": level.value,
                "tags": {"level": level.name},
            },
            config=context.config,
        ),
    )
```

## Tools System

### Tool Definition

A **tool** is a capability that the harness can invoke to perform specific actions (WebSearch, WebFetch, Read, Write, Bash, Skill).

### Tool Schema

Each tool has a defined schema:

```python
@dataclass(frozen=True)
class ToolDefinition:
    """Definition of a tool available to the harness."""

    name: str
    description: str
    parameters: dict[str, ToolParameter]
    required_permissions: list[str]
    output_schema: dict[str, Any]

@dataclass(frozen=True)
class ToolParameter:
    """Definition of a tool parameter."""

    name: str
    type: str  # "string", "integer", "boolean", "object", "array"
    description: str
    required: bool
    default: Any = None
    enum: list[Any] | None = None
```

### Available Tools

| Tool | Description | Parameters | Output |
|------|-------------|------------|--------|
| **WebSearch** | Search the web for information | query, recency_filter | Search results with URLs |
| **WebFetch** | Fetch content from a URL | url, prompt | Fetched content |
| **Read** | Read a file from filesystem | file_path, offset, limit | File contents |
| **Write** | Write content to a file | file_path, content | Confirmation |
| **Bash** | Execute shell command | command, timeout | Command output |
| **Skill** | Invoke a sub-skill | skill, args | Sub-skill result |

### Tool Implementation

The tools system provides type-safe wrappers around raw tool calls:

```python
class ToolExecutor:
    """Type-safe tool executor with validation."""

    def __init__(self, config: SystemConfig) -> None:
        self.config = config

    def web_search(
        self,
        query: str,
        recency_filter: str | None = None,
    ) -> list[dict[str, Any]]:
        """Search the web with validation.

        Args:
            query: Search query (required)
            recency_filter: Optional time filter ("oneWeek", "oneMonth", etc.)

        Returns:
            List of search results with URLs, titles, snippets

        Raises:
            ToolError: If search fails or returns no results
        """
        if not query or not query.strip():
            raise ToolError("Query cannot be empty")

        # Invoke WebSearch tool
        results = WebSearch(
            query=query,
            recency=recency_filter,
        )

        if not results:
            raise ToolError(f"No results for query: {query}")

        return results

    def web_fetch(self, url: str, prompt: str | None = None) -> str:
        """Fetch content from a URL with validation.

        Args:
            url: URL to fetch (required)
            prompt: Optional processing prompt

        Returns:
            Fetched content as string

        Raises:
            ToolError: If fetch fails or URL is invalid
        """
        if not url or not url.strip():
            raise ToolError("URL cannot be empty")

        # Basic URL validation
        if not url.startswith(("http://", "https://")):
            raise ToolError(f"Invalid URL: {url}")

        # Invoke WebFetch tool
        content = WebFetch(
            url=url,
            prompt=prompt or "Extract the main content",
        )

        return content

    def read_file(
        self,
        file_path: str,
        offset: int = 0,
        limit: int | None = None,
    ) -> str:
        """Read a file with validation.

        Args:
            file_path: Path to file (required)
            offset: Starting line number
            limit: Maximum lines to read

        Returns:
            File contents as string

        Raises:
            ToolError: If file doesn't exist or read fails
        """
        if not file_path:
            raise ToolError("File path cannot be empty")

        # Invoke Read tool
        content = Read(
            file_path=file_path,
            offset=offset,
            limit=limit,
        )

        return content

    def invoke_skill(
        self,
        skill_name: str,
        args: str | None = None,
    ) -> dict[str, Any]:
        """Invoke a sub-skill with validation.

        Args:
            skill_name: Name of skill to invoke (required)
            args: Optional arguments to pass

        Returns:
            Sub-skill result as dictionary

        Raises:
            ToolError: If skill not found or invocation fails
        """
        valid_skills = [
            "sub-gather-requirements",
            "sub-evidence-collector",
            "sub-core-analysis",
            "sub-knowledge-updater",
            "sub-advisor",
        ]

        if skill_name not in valid_skills:
            raise ToolError(f"Unknown skill: {skill_name}")

        # Invoke Skill tool
        result = Skill(
            skill=skill_name,
            args=args,
        )

        return result
```

### Tool Usage by Sub-Skills

Each sub-skill declares its tool dependencies:

```markdown
## Tools

- **WebSearch** / **WebFetch** - Fetch live domain data
- **Read** - Read SECOND-KNOWLEDGE-BRAIN.md
- **Skill** - Invoke other sub-skills (main only)
```

### Tool Permissions

Tools require specific permissions:

| Tool | Required Permissions |
|------|---------------------|
| WebSearch | network:outbound |
| WebFetch | network:outbound |
| Read | filesystem:read |
| Write | filesystem:write |
| Bash | shell:execute |
| Skill | skill:invoke |

Permissions are checked at runtime:

```python
def check_permission(tool_name: str, required_permission: str) -> None:
    """Check if tool has required permission."""
    if not has_permission(required_permission):
        raise PermissionError(
            f"Tool {tool_name} requires permission {required_permission}"
        )
```

## Integration with Harness

### Hook Integration Points

The harness invokes hooks at these points:

```python
def execute_harness(user_query: str) -> dict:
    hook_handler = HookHandler()
    tool_executor = ToolExecutor(get_system_config())

    # Pre-harness hook
    hook_handler.emit(
        HookName.PRE_HARNESS,
        HookContext(
            hook_name=HookName.PRE_HARNESS,
            parameters={"query": user_query},
            config=get_system_config(),
        ),
    )

    try:
        # Step 1
        hook_handler.emit(
            HookName.PRE_STEP_1,
            HookContext(hook_name=HookName.PRE_STEP_1, ...),
        )
        result_1 = tool_executor.invoke_skill("sub-gather-requirements")
        hook_handler.emit(
            HookName.POST_STEP_1,
            HookContext(
                hook_name=HookName.POST_STEP_1,
                parameters={"result": result_1},
                config=get_system_config(),
            ),
        )

        # ... continue for all steps

        # Quality gates
        hook_handler.emit(
            HookName.PRE_QUALITY_GATE,
            HookContext(hook_name=HookName.PRE_QUALITY_GATE, ...),
        )
        result = apply_quality_gates(final_output)
        hook_handler.emit(
            HookName.POST_QUALITY_GATE,
            HookContext(
                hook_name=HookName.POST_QUALITY_GATE,
                parameters={"result": result},
                config=get_system_config(),
            ),
        )

        # Post-harness hook
        hook_handler.emit(
            HookName.POST_HARNESS,
            HookContext(
                hook_name=HookName.POST_HARNESS,
                parameters={"result": result},
                config=get_system_config(),
            ),
        )

        return result

    except Exception as e:
        # Error hook
        hook_handler.emit(
            HookName.ON_ERROR,
            HookContext(
                hook_name=HookName.ON_ERROR,
                parameters={"error": e, "context": {}},
                config=get_system_config(),
            ),
        )
        raise
```

## Extension Points

### Custom Hooks

Users can register custom hooks:

```python
# Register a custom pre-step hook
hook_handler.register(
    HookName.PRE_STEP_2,
    lambda ctx: log.info("About to collect evidence", context=ctx.parameters)
)

# Register a custom metric emitter
hook_handler.register(
    HookName.EMIT_METRIC,
    lambda ctx: send_to_prometheus(
        metric=ctx.parameters["metric"],
        value=ctx.parameters["value"],
        tags=ctx.parameters.get("tags", {}),
    )
)
```

### Custom Tools

Additional tools can be added by extending the ToolExecutor:

```python
class CustomToolExecutor(ToolExecutor):
    """Custom tool executor with additional tools."""

    def custom_tool(self, param: str) -> str:
        """Custom tool implementation."""
        # Custom logic here
        return result
```

## Best Practices

### Hook Best Practices

1. **Keep handlers simple** - Hooks should be fast and reliable
2. **Handle exceptions** - Never let a hook handler crash the harness
3. **Use hooks for cross-cutting concerns** - Logging, metrics, validation
4. **Avoid state mutations** - Hooks should observe, not modify (unless intentional)

### Tool Best Practices

1. **Validate inputs** - Always validate tool parameters
2. **Handle errors gracefully** - Provide clear error messages
3. **Log tool usage** - Track which tools are used and how often
4. **Respect permissions** - Check permissions before invoking tools

## Future Enhancements

### Planned Hook Enhancements

- [ ] Async hook handlers for better performance
- [ ] Hook prioritization (high/medium/low)
- [ ] Hook chaining (output of one hook to next)
- [ ] Hook conditionals (execute only when condition met)

### Planned Tool Enhancements

- [ ] Tool result caching with TTL
- [ ] Tool rate limiting
- [ ] Tool retry with exponential backoff
- [ ] Tool execution metrics

## Version History

- **v1.1.0** - Initial hooks and tools system design (2025-07-28)

---

*This document describes the hooks and tools system as implemented in the indie-game-match-history-database harness.*
