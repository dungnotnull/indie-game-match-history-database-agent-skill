# References Directory

This directory contains comprehensive reference materials for the indie-game-match-history-database skill and engine.

## Structure

```
references/
├── domain/           # Domain knowledge and best practices
├── prompts/          # Prompt templates for sub-skills
├── architecture/     # Architecture patterns and design decisions
└── README.md         # This file
```

## Domain Knowledge (`domain/`)

Authoritative reference materials for indie game match-history data engineering:

- `rating_systems.md` - ELO, Glicko-1, Glicko-2, TrueSkill comparison
- `storage_patterns.md` - Hot/warm/cold tiering, indexing strategies
- `privacy_laws.md` - GDPR, COPPA, CCPA compliance requirements
- `replay_formats.md` - Replay blob formats, compression, content addressing
- `leaderboard_design.md` - ZSET, pagination, tie-breaking strategies
- `scalability_patterns.md` - Sharding, partitioning, batch processing

## Prompt Templates (`prompts/`)

Base prompt templates used by sub-skills for consistent, high-quality outputs:

- `gather_requirements.md` - Template for requirements gathering
- `evidence_collection.md` - Template for evidence collection
- `core_analysis.md` - Template for storage architecture analysis
- `knowledge_update.md` - Template for knowledge base updates
- `advisor_synthesis.md` - Template for final recommendation synthesis

## Architecture (`architecture/`)

System architecture documentation and design patterns:

- `data_model.md` - Core data model (Player, Match, Rating, etc.)
- `storage_architecture.md` - Tiered storage design and tradeoffs
- `query_patterns.md` - Common query patterns and optimization
- `privacy_pipeline.md` - GDPR/COPPA pipeline architecture
- `schema_evolution.md` - Migration strategy and versioning

## Usage

These materials are used by:

1. **Sub-skills** - Domain knowledge informs analysis and recommendations
2. **Knowledge crawler** - Identifies authoritative sources and gaps
3. **Engine package** - Implements the patterns and designs documented here
4. **Quality gates** - Validates outputs against documented best practices

## Contributing

When updating domain knowledge:

1. Add new references with DOI/URL for traceability
2. Include date of access for web resources
3. Tag sources with tier (Tier 1: peer-reviewed, Tier 2: industry standards, etc.)
4. Cross-reference with engine implementation where applicable

## Version History

- v1.1.0 - Initial comprehensive reference set (2025)
