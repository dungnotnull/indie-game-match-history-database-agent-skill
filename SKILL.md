---
name: indie-game-match-history-database
description: Historical Match Database Architecture & Engine for Indie Games - Comprehensive evidence-backed analysis harness for indie game match-history data engineering. Use when designing storage architectures, selecting rating systems (ELO/Glicko-2), implementing tiered storage, addressing GDPR/COPPA privacy requirements, or building leaderboards. Grounded in a production-tested Python engine implementing all analyzed patterns. Invoke for any match-history database design, scalability assessment, or privacy compliance analysis.
---

# Indie Game Match-History Database Skill Registry

## Overview

This skill provides a comprehensive, evidence-backed analytical workflow for **Indie Game Match-History Data Engineering**. It combines real-time data aggregation, recognized domain methods, academic research, and a production-tested engine into a single orchestrated harness that delivers risk-disclosed, fully-evidenced recommendations.

## Architecture Pattern

```
┌─────────────────────────────────────────────────────────────────────┐
│                         MAIN HARNESS                                │
│                    (skills/main.md)                                 │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  Pre-Flight: Language Detection (vi/en)                     │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                  │                                 │
│                                  ▼                                 │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  Step 1: sub-gather-requirements                            │  │
│  │  → Object, scope, timeframe, inputs, audience, language     │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                  │                                 │
│                                  ▼                                 │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  Step 2: sub-evidence-collector                             │  │
│  │  → Current data, authoritative docs, recent news            │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                  │                                 │
│                                  ▼                                 │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  Step 3: sub-core-analysis                                  │  │
│  │  → Data model, tiering, queries, scalability, privacy       │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                  │                                 │
│                                  ▼                                 │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  Step 4: sub-knowledge-updater                              │  │
│  │  → Academic evidence, tiered citations, gap flags           │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                  │                                 │
│                                  ▼                                 │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  Step 5: sub-advisor                                        │  │
│  │  → Risk-disclosed conclusion, evidence chain, actions        │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                  │                                 │
│                                  ▼                                 │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  Step 6: Quality Gate Review                                │  │
│  │  → 10 gates (U1-U6 + G1-G4) with auto-fix                   │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                  │                                 │
│                                  ▼                                 │
│                      Deliver Output                               │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                    ENGINE GROUNDING LAYER                            │
│                    (indie_match_history/)                            │
│  ┌─────────────┬──────────────┬──────────────┬─────────────────┐   │
│  │  models.py  │  ratings.py  │  storage/    │  leaderboard.py │   │
│  │  (Player,   │  (ELO,       │  (tiered,    │  (ZSET,         │   │
│  │   Match,    │   Glicko-2)  │   sqlite,    │   bisect)       │   │
│  │   Rating)   │              │   memory)    │                 │   │
│  └─────────────┴──────────────┴──────────────┴─────────────────┘   │
│  ┌──────────────┬──────────────┬──────────────┬───────────────┐   │
│  │  replay.py   │  privacy.py  │  engine.py   │  schema.py    │   │
│  │  (gzip,      │  (GDPR,      │  (facade)    │  (migrations) │   │
│  │   SHA-256)   │   COPPA)     │              │               │   │
│  └──────────────┴──────────────┴──────────────┴───────────────┘   │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                      KNOWLEDGE BASE                                  │
│                   (SECOND-KNOWLEDGE-BRAIN.md)                        │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Academic papers (Tier 1) - ArXiv, Semantic Scholar         │   │
│  │  Industry standards (Tier 2) - GDPR, COPPA, rating docs      │   │
│  │  Implementation guides (Tier 3) - Blogs, tutorials            │   │
│  │  Update log - Crawl pipeline entries with timestamps          │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

## Skill Registration

### Main Skill

**File:** `skills/main.md`

**Registration:**
```yaml
name: indie-game-match-history-database
description: Historical Match Database Architecture & Engine for Indie Games
```

**Trigger Phrases:**
- "Design match-history storage"
- "Which rating system for my game"
- "GDPR compliance for player data"
- "Tiered storage architecture"
- "Leaderboard design patterns"
- "Match data scalability"

**Input Schema:**
```json
{
  "type": "object",
  "properties": {
    "query": {
      "type": "string",
      "description": "User's analysis request"
    },
    "context": {
      "type": "object",
      "properties": {
        "game_type": {"type": "string"},
        "player_count": {"type": "integer"},
        "match_volume": {"type": "string"},
        "region": {"type": "string"}
      }
    }
  },
  "required": ["query"]
}
```

**Output Schema:**
```json
{
  "type": "object",
  "properties": {
    "language": {"type": "string", "enum": ["en", "vi"]},
    "inputs_and_scope": {
      "type": "object",
      "properties": {
        "object_of_analysis": {"type": "string"},
        "scope": {"type": "string"},
        "timeframe": {"type": "string"},
        "available_inputs": {"type": "array"},
        "target_audience": {"type": "string"}
      }
    },
    "evidence_collected": {
      "type": "object",
      "properties": {
        "current_data": {"type": "object"},
        "authoritative_docs": {"type": "array"},
        "recent_news": {"type": "array"}
      }
    },
    "analysis": {
      "type": "object",
      "properties": {
        "data_model": {"type": "object"},
        "tiering": {"type": "object"},
        "queries_and_indexes": {"type": "object"},
        "scalability": {"type": "object"},
        "privacy_and_retention": {"type": "object"}
      }
    },
    "academic_evidence": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "title": {"type": "string"},
          "authors": {"type": "array"},
          "year": {"type": "integer"},
          "tier": {"type": "string", "enum": ["1", "2", "3", "4"]},
          "doi": {"type": "string"},
          "relevance": {"type": "string"}
        }
      }
    },
    "verdict": {
      "type": "string",
      "enum": [
        "Scalable Schema",
        "Conditional (scale)",
        "Unscalable/Non-private",
        "Inconclusive"
      ]
    },
    "key_risks": {"type": "array"},
    "evidence_chain": {"type": "object"},
    "recommended_actions": {"type": "array"},
    "disclosure": {"type": "string"}
  },
  "required": ["language", "verdict", "disclosure"]
}
```

### Sub-Skills

#### 1. sub-gather-requirements

**File:** `skills/sub-gather-requirements.md`

**Purpose:** Clarify object of analysis, constraints, timeframe, inputs, audience, language

**Input Schema:**
```json
{
  "type": "object",
  "properties": {
    "raw_user_message": {"type": "string"},
    "provided_materials": {"type": "array"}
  }
}
```

**Output Schema:**
```json
{
  "type": "object",
  "properties": {
    "object": {"type": "string"},
    "scope": {"type": "string"},
    "timeframe": {"type": "string"},
    "available_inputs": {"type": "array"},
    "target_audience": {"type": "string"},
    "language": {"type": "string", "enum": ["en", "vi"]},
    "analysis_type": {"type": "string"}
  },
  "required": ["object", "language"]
}
```

#### 2. sub-evidence-collector

**File:** `skills/sub-evidence-collector.md`

**Purpose:** Fetch authoritative real-time and reference data

**Input Schema:**
```json
{
  "type": "object",
  "properties": {
    "object": {"type": "string"},
    "scope": {"type": "string"},
    "timeframe": {"type": "string"},
    "language": {"type": "string"}
  }
}
```

**Output Schema:**
```json
{
  "type": "object",
  "properties": {
    "current_data": {
      "type": "object",
      "properties": {
        "source": {"type": "string"},
        "date_fetched": {"type": "string"},
        "data": {},
        "confidence": {"type": "string"}
      }
    },
    "authoritative_docs": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "title": {"type": "string"},
          "source": {"type": "string"},
          "type": {"type": "string"},
          "tier": {"type": "string"},
          "key_points": {"type": "array"},
          "date_accessed": {"type": "string"}
        }
      }
    },
    "recent_news": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "title": {"type": "string"},
          "source": {"type": "string"},
          "date": {"type": "string"},
          "relevance": {"type": "string"}
        }
      }
    },
    "knowledge_base_entries": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "title": {"type": "string"},
          "authors": {"type": "array"},
          "year": {"type": "integer"},
          "tier": {"type": "string"},
          "doi": {"type": "string"},
          "relevance_to_analysis": {"type": "string"}
        }
      }
    }
  }
}
```

#### 3. sub-core-analysis

**File:** `skills/sub-core-analysis.md`

**Purpose:** Design storage architecture grounded in engine implementation

**Input Schema:**
```json
{
  "type": "object",
  "properties": {
    "game": {"type": "string"},
    "expected_player_volume": {"type": "integer"},
    "expected_match_volume": {"type": "string"},
    "leaderboards": {"type": "boolean"},
    "replays": {"type": "boolean"},
    "language": {"type": "string"}
  }
}
```

**Output Schema:**
```json
{
  "type": "object",
  "properties": {
    "data_model": {
      "type": "object",
      "properties": {
        "core_entities": {"type": "array"},
        "relationships": {"type": "array"},
        "constraints": {"type": "array"},
        "engine_implementation": {"type": "string"}
      }
    },
    "tiering": {
      "type": "object",
      "properties": {
        "hot_retention_days": {"type": "integer"},
        "warm_retention_days": {"type": "integer"},
        "cold_retention_days": {"type": "integer"},
        "migration_strategy": {"type": "string"},
        "cost_estimate": {"type": "string"}
      }
    },
    "queries_and_indexes": {
      "type": "object",
      "properties": {
        "primary_queries": {"type": "array"},
        "secondary_indexes": {"type": "array"},
        "optimization_patterns": {"type": "array"}
      }
    },
    "scalability": {
      "type": "object",
      "properties": {
        "horizontal_scaling": {"type": "string"},
        "vertical_scaling": {"type": "string"},
        "bottleneck_analysis": {"type": "array"},
        "recommended_architecture": {"type": "string"}
      }
    },
    "privacy_and_retention": {
      "type": "object",
      "properties": {
        "gdpr_compliance": {"type": "boolean"},
        "coppa_compliance": {"type": "boolean"},
        "retention_aging": {"type": "boolean"},
        "right_to_erasure": {"type": "string"},
        "engine_implementation": {"type": "string"}
      }
    }
  }
}
```

#### 4. sub-knowledge-updater

**File:** `skills/sub-knowledge-updater.md`

**Purpose:** Query knowledge base for academic evidence, surface citations, flag gaps

**Input Schema:**
```json
{
  "type": "object",
  "properties": {
    "topic_keywords": {"type": "array"},
    "analysis_type": {"type": "string"}
  }
}
```

**Output Schema:**
```json
{
  "type": "object",
  "properties": {
    "citations": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "title": {"type": "string"},
          "authors": {"type": "array"},
          "year": {"type": "integer"},
          "tier": {"type": "string"},
          "doi": {"type": "string"},
          "relevance": {"type": "string"},
          "key_findings": {"type": "array"}
        }
      }
    },
    "coverage_rating": {"type": "string"},
    "gaps_flagged": {"type": "array"},
    "recommended_search_terms": {"type": "array"}
  }
}
```

#### 5. sub-advisor

**File:** `skills/sub-advisor.md`

**Purpose:** Synthesize risk-disclosed conclusion with evidence chain

**Input Schema:**
```json
{
  "type": "object",
  "properties": {
    "core_analysis": {"type": "object"},
    "evidence_bundle": {"type": "object"},
    "knowledge_evidence": {"type": "array"},
    "language": {"type": "string"}
  }
}
```

**Output Schema:**
```json
{
  "type": "object",
  "properties": {
    "verdict": {
      "type": "string",
      "enum": [
        "Scalable Schema",
        "Conditional (scale)",
        "Unscalable/Non-private",
        "Inconclusive"
      ]
    },
    "confidence": {"type": "string"},
    "scenarios": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "scenario": {"type": "string"},
          "outcome": {"type": "string"},
          "probability": {"type": "string"}
        }
      }
    },
    "key_risks": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "risk": {"type": "string"},
          "severity": {"type": "string"},
          "mitigation": {"type": "string"}
        }
      }
    },
    "evidence_chain": {
      "type": "object",
      "properties": {
        "primary_sources": {"type": "array"},
        "secondary_sources": {"type": "array"},
        "traceability": {"type": "boolean"}
      }
    },
    "recommended_actions": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "action": {"type": "string"},
          "priority": {"type": "string"},
            "engine_reference": {"type": "string"}
        }
      }
    },
    "disclosure": {
      "type": "string",
      "description": "Must appear BEFORE the verdict"
    }
  },
  "required": ["verdict", "disclosure"]
}
```

## Skill Resolution

### Resolution Order

When `/indie-game-match-history-database` is invoked:

1. **Main skill loads** → `skills/main.md`
2. **Pre-flight executes** → Language detection (vi/en)
3. **Sub-skills resolve** → Each sub-skill loads on-demand
4. **Engine loads** → `indie_match_history/` modules imported
5. **Knowledge base loads** → `SECOND-KNOWLEDGE-BRAIN.md` read

### Resolution Failures

| Failure Mode | Action | Degradation Level |
|--------------|--------|-------------------|
| Sub-skill not found | Abort with error | 4 (Harness failed) |
| Engine module import failed | Abort with error | 4 (Harness failed) |
| Knowledge base missing | Continue without cache | 1 (Real-time unavailable) |
| Language detection failed | Default to English | 0 (Full capability) |

### Graceful Degradation

The harness operates at 5 levels:

```python
class DegradationLevel(Enum):
    LEVEL_0 = "Full capability"
    LEVEL_1 = "Real-time data unavailable (using cached)"
    LEVEL_2 = "Knowledge base unavailable (expert judgment only)"
    LEVEL_3 = "Sub-skill unavailable (manual analysis)"
    LEVEL_4 = "Harness failed (cannot complete)"
```

At each level, a `LIMITATION` banner is added to the output:

```markdown
---
⚠️ LIMITATION: This analysis was conducted at Degradation Level {N}.
{Explanation of what's unavailable and impact on confidence.
---
```

## Quality Gates

### Universal Gates (U1-U6)

Applied to ALL analyses:

| Gate | Criterion | Auto-Fix | Max Retries |
|------|-----------|----------|------------|
| U1 | ≥3 sources, ≥1 academic/authoritative | Search knowledge base | 2 |
| U2 | Disclosure before conclusion | Prepend disclosure | 2 |
| U3 | Evidence hierarchy stated | Add tier labels | 2 |
| U4 | Language matches preference | Translate output | 1 |
| U5 | Output template complete | Fill missing sections | 2 |
| U6 | Claims traceable to sources | Add references | 2 |

### Domain Gates (G1-G4)

Specific to match-history data engineering:

| Gate | Criterion | Engine Module | Auto-Fix |
|------|-----------|---------------|----------|
| G1 | Data model & tiering defined | `models.py`, `storage/tiered.py` | Reference docs |
| G2 | Queries & indexes designed | `storage/base.py` | Add default indexes |
| G3 | Scalability addressed | `storage/sqlite.py` | Add scaling notes |
| G4 | Privacy/retention addressed | `privacy.py` | Add privacy warning |

### Gate Enforcement

```python
class QualityGateResult(Enum):
    PASS = "Gate passed"
    AUTO_FIXED = "Gate passed after auto-fix"
    FAILED = "Gate failed after retries"
    SKIPPED = "Gate skipped (degraded mode)"
```

## Execution Flow

### Sequential Flow

```python
def execute_harness(user_query: str) -> dict:
    # Step 1: Gather requirements
    requirements = invoke_sub_skill("sub-gather-requirements", user_query)
    if not requirements["object"]:
        return error("No object of analysis")

    # Step 2: Collect evidence
    evidence = invoke_sub_skill("sub-evidence-collector", requirements)
    if not evidence["current_data"] and not evidence["authoritative_docs"]:
        add_limitation("Real-time data unavailable")

    # Step 3: Core analysis
    analysis = invoke_sub_skill("sub-core-analysis", requirements)

    # Step 4: Knowledge update
    knowledge = invoke_sub_skill("sub-knowledge-updater", analysis)

    # Step 5: Synthesis
    conclusion = invoke_sub_skill("sub-advisor", {
        "analysis": analysis,
        "evidence": evidence,
        "knowledge": knowledge,
    })

    # Step 6: Quality gates
    result = apply_quality_gates(conclusion)

    return result
```

### Parallel Execution

When `enable_parallel_subskills = true`:

```python
# Steps 2-4 can run in parallel
with ThreadPoolExecutor(max_workers=3) as executor:
    future_evidence = executor.submit(invoke_sub_skill, "sub-evidence-collector", requirements)
    future_analysis = executor.submit(invoke_sub_skill, "sub-core-analysis", requirements)
    future_knowledge = executor.submit(invoke_sub_skill, "sub-knowledge-updater", analysis)

    evidence = future_evidence.result()
    analysis = future_analysis.result()
    knowledge = future_knowledge.result()
```

## Tool Requirements

Each sub-skill requires specific tools:

| Sub-Skill | Tools Required |
|-----------|----------------|
| main | Skill (invoke sub-skills), Read (knowledge base) |
| sub-gather-requirements | Conversation only |
| sub-evidence-collector | WebSearch, WebFetch, Read (knowledge base) |
| sub-core-analysis | Read (knowledge base, engine), WebFetch, reasoning |
| sub-knowledge-updater | Read (knowledge base), WebSearch (gap fill) |
| sub-advisor | Reasoning, Read (knowledge base) |

## Engine Grounding

All analysis recommendations are grounded in the tested engine:

| Analysis Area | Engine Module | Validation |
|--------------|---------------|------------|
| Data model | `models.py` | 99 tests |
| Rating systems | `ratings.py` | Deterministic unit tests |
| Tiered storage | `storage/tiered.py` | Integration tests |
| SQLite backend | `storage/sqlite.py` | Schema migration tests |
| Leaderboards | `leaderboard.py` | Performance tests |
| Replay storage | `replay.py` | SHA-256 validation tests |
| Privacy pipeline | `privacy.py` | GDPR/COPPA tests |

## Knowledge Pipeline

### Crawl Configuration

```python
KNOWLEDGE_CONFIG = {
    "keywords": [
        "match history", "rating system", "tiered storage",
        "leaderboard", "GDPR gaming", "COPPA compliance",
        "ELO", "Glicko-2", "TrueSkill", "game database"
    ],
    "arxiv_categories": ["cs.DB", "cs.GT"],
    "rss_feeds": [
        "https://arxiv.org/rss/cs.DB",
        "https://arxiv.org/rss/cs.GT"
    ],
    "scoring_weights": {
        "recency": 0.4,
        "relevance": 0.4,
        "citations": 0.2
    },
    "min_score_threshold": 3.0
}
```

### Crawl Schedule

```cron
# Weekly academic update (Mondays 8:00 AM)
0 8 * * 1 python tools/knowledge_updater.py >> logs/knowledge_update.log 2>&1

# Daily news update (Daily 7:00 AM)
0 7 * * * python tools/knowledge_updater.py --news-only >> logs/knowledge_news.log 2>&1
```

## Validation

### Test Coverage

- **Unit tests**: 99 tests covering all engine modules
- **Integration tests**: Tiered storage, migrations, end-to-end
- **Scenario tests**: 5 scenarios validating harness behavior
- **Validation tests**: Structural and content validators

Run tests:

```bash
# Unit tests
pytest -q

# Scenario tests
python tools/run_test_scenarios.py

# Knowledge updater tests
python tools/test_knowledge_updater.py
```

## Configuration

### Environment Variables

```bash
# Paths
INDIE_MATCH_PROJECT_ROOT=/path/to/project
INDIE_MATCH_DATA_ROOT=/path/to/data
INDIE_MATCH_DATABASE_PATH=/path/to/matches.db
INDIE_MATCH_REPLAY_ROOT=/path/to/replays
INDIE_MATCH_LOG_ROOT=/path/to/logs

# LLM
INDIE_MATCH_LLM_PROVIDER=anthropic
INDIE_MATCH_LLM_MODEL=claude-sonnet-4-6
INDIE_MATCH_LLM_TEMPERATURE=0.7

# Features
INDIE_MATCH_ENABLE_TIERED_STORAGE=true
INDIE_MATCH_ENABLE_GDPR_PIPELINE=true
INDIE_MATCH_ENABLE_COPPA_COMPLIANCE=true

# Knowledge
INDIE_MATCH_ENABLE_CRAWL=true
INDIE_MATCH_CRAWL_INTERVAL_HOURS=24
```

### Feature Flags

```python
FeatureFlags(
    enable_tiered_storage=True,
    enable_replay_compression=True,
    enable_gdpr_pipeline=True,
    enable_coppa_compliance=True,
    enable_leaderboard_caching=True,
    enable_schema_migrations=True,
    enable_structured_logging=True,
    enable_metrics_export=False,
    enable_telemetry=False,
)
```

## Output Template

All outputs MUST use this structure:

```markdown
# {Analysis Report}

## Inputs & Scope
- Object of analysis: {object}
- Scope: {scope}
- Timeframe: {timeframe}
- Available inputs: {inputs}
- Target audience: {audience}

## Evidence Collected
### Current Data
- Source: {source}
- Date: {date}
- Confidence: {high/medium/low}

### Authoritative Documents
1. [{Title}]({URL}) (Tier {N})
   - Key points: {points}

## Analysis / Scorecard
### Data Model
{analysis of data model}

### Tiering Strategy
{analysis of tiering}

### Queries & Indexes
{analysis of query patterns}

### Scalability Assessment
{analysis of scalability}

### Privacy & Retention
{analysis of privacy requirements}

## Academic Evidence
1. {Authors} ({Year}): {Title}. {DOI}. Tier {N}.
   - Relevance: {why it matters}

## Verdict / Conclusion
{verdict}

Confidence: {high/medium/low}

### Key Risks
{risk list}

### Evidence Chain
{traceability of claims to sources}

## Recommended Actions
{priority-ordered actions with engine references}

## Disclosure / Limitations
{what couldn't be analyzed, data gaps, assumptions}
```

## Version History

- **v1.1.0** - Production-ready with comprehensive engine grounding
- **v1.0.0** - Initial release with basic harness

## License

MIT License - See LICENSE file for details.
