# Changelog

All notable changes to this project are documented here.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2026-07-14
### Added
- Real production-grade Python package `indie_match_history` implementing the full
  match-history database engine: typed data models, ELO + Glicko-2 rating engines,
  pluggable storage backends (in-memory, SQLite, tiered hot/warm/cold), ZSET-style
  sorted-set leaderboards, compressed replay blob storage, and a GDPR/COPPA
  retention & deletion pipeline.
- `imh` CLI for players, matches, leaderboards, replays, retention, and ratings.
- Full `pytest` suite across models, ratings, storage, leaderboard, replay,
  privacy, engine, schema, and CLI.
- `pyproject.toml`, `LICENSE`, `CHANGELOG.md`, `CONTRIBUTING.md`, `SECURITY.md`.
- Structured logging, typed error hierarchy, schema versioning & migrations.
### Changed
- Knowledge pipeline and skill harness upgraded to v1.1.0 references.
- Validators extended to assert on the new package layout and tests.

## [1.0.0] - 2026-07-10
### Added
- Claude Code skill harness, 5 sub-skills, quality gates, knowledge crawl pipeline.
- SECOND-KNOWLEDGE-BRAIN.md seeded knowledge base.
- Structural validators and test scenarios.