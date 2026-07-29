# Assets Directory

This directory contains static resources for the indie-game-match-history-database project.

## Structure

```
assets/
├── diagrams/         # System and architecture diagrams
├── schemas/          # Database schema visualizations
└── README.md         # This file
```

## Diagrams (`diagrams/`)

System architecture and flow diagrams in Mermaid format:

- `harness_flow.md` - End-to-end harness execution flow
- `data_model.md` - Core data model relationships
- `storage_architecture.md` - Tiered storage architecture
- `privacy_pipeline.md` - GDPR/COPPA pipeline flow
- `rating_flow.md` - Rating system update flow

### Viewing Diagrams

These diagrams are in Mermaid format. View them using:

1. **Mermaid Live Editor**: https://mermaid.live
2. **GitHub/GitLab**: Rendered natively in markdown
3. **VS Code**: With Mermaid preview extension
4. **CLI**: `mmdc -i diagram.md -o diagram.png`

## Schemas (`schemas/`)

Database schema definitions and visualizations:

- `v1_schema.md` - Version 1 schema (initial)
- `v2_schema.md` - Version 2 schema (added replay metadata)
- `v3_schema.md` - Version 3 schema (added privacy fields)

### Schema Evolution

The database schema is versioned with automatic migrations:

```python
from indie_match_history.schema import migrate, SCHEMA_VERSION

# Get current version
print(f"Current schema: {SCHEMA_VERSION}")

# Migrate storage
migrate(storage, to_version=SCHEMA_VERSION)
```

See `indie_match_history/schema.py` for migration implementations.

## Usage

These assets are used for:

1. **Documentation** - README.md, PROJECT-detail.md
2. **Onboarding** - Understanding the system architecture
3. **Analysis** - Sub-skills reference these for design decisions
4. **Validation** - Ensuring implementation matches documented architecture

## Contributing

When adding diagrams:

1. Use Mermaid format for portability
2. Include a brief description of what the diagram shows
3. Cross-reference with engine implementation
4. Update this README if adding new diagram types

When updating schemas:

1. Update both the schema file AND schema.py
2. Add a migration in schema.py
3. Update the version number
4. Document breaking changes

## License

These assets are part of the indie-game-match-history-database project and inherit its license (MIT).
