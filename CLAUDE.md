# CLAUDE.md - Skill 263: indie-game-match-history-database

## Skill Identity
- **Skill Name:** `indie-game-match-history-database`
- **Tagline:** Historical Match Database Architecture & Engine for Indie
  Multiplayer Games - Indie Game Match-History Data Engineering analysis &
  decision-support harness backed by a runnable, tested Python engine.
- **Current Phase:** Phase 5 - Integration & Polish (PRODUCTION READY v1.1.0)
- **Folder:** `D:\972026\263-indie-game-match-history-database\`

---

## Problem This Skill Solves

This skill provides a structured, evidence-backed analytical workflow for
**Indie Game Match-History Data Engineering**. It gathers authoritative
real-time and reference data, applies recognized domain methods, cross-references
academic research, and delivers actionable outputs that are fully evidenced,
risk/limitation-disclosed, and traceable to authoritative sources -
continuously self-improving through an automated knowledge crawl pipeline.

Crucially, the skill is grounded in a real, tested engine package
(`indie_match_history/`) implementing the data model, ELO/Glicko-2 ratings,
tiered storage, leaderboards, replay blobs, and GDPR/COPPA retention it
analyses - so recommendations reference runnable code, not prose.

---

## Harness Flow Summary

```
/indie-game-match-history-database invoked
|
+-- Step 1: sub-gather-requirements   -> clarify object, scope, timeframe, inputs, audience, language
+-- Step 2: sub-evidence-collector    -> fetch authoritative real-time + reference + academic data
+-- Step 3: sub-core-analysis         -> design storage: model, tiering, queries, scale, replay, privacy
+-- Step 4: sub-knowledge-updater     -> query SECOND-KNOWLEDGE-BRAIN.md; surface tiered citations
+-- Step 5: sub-advisor               -> synthesize risk-disclosed conclusion + evidence chain
+-- Step 6: main (quality gate)        -> verify evidence hierarchy, disclosure, output polish
```

See `skills/main.md` for the full protocol, Pre-Flight language detection,
10 quality gates (U1-U6 + G1-G4), graceful degradation levels 0-4, the error
recovery table, and the mandatory output template.

---

## Sub-Skills

| File | Purpose |
|------|---------|
| `skills/sub-gather-requirements.md` | Clarify object of analysis, constraints, timeframe, inputs, audience, language before any data fetching. |
| `skills/sub-evidence-collector.md` | Fetch authoritative real-time and reference data: status/parameters, docs/standards, recent developments. |
| `skills/sub-core-analysis.md` | Design historical match-data storage: model, tiering, queries, scale, replay, privacy. |
| `skills/sub-knowledge-updater.md` | Query SECOND-KNOWLEDGE-BRAIN.md; surface tiered citations; flag gaps for the crawl pipeline. |
| `skills/sub-advisor.md` | Synthesize risk-disclosed conclusion with full evidence chain and recommended actions. |

---

## Engine Package (`indie_match_history/`)

The analysis is backed by a production-grade engine:
- `models.py` - immutable typed records (Player, Match, MatchResult, MatchEvent, ReplayRef, Rating)
- `ratings.py` - ELO + Glicko-2 engines (pure, deterministic)
- `storage/` - base, in-memory, SQLite (auto-migrating), tiered hot/warm/cold
- `leaderboard.py` - ZSET-style sorted set (bisect-backed)
- `replay.py` - content-addressed, gzip-compressed, SHA-256-verified replay blobs
- `privacy.py` - retention aging + replay expiry + GDPR/COPPA erasure
- `engine.py` - `MatchHistoryEngine` facade
- `cli.py` - `imh` CLI
- `schema.py` - versioned migrations (v1->v3)

Run: `pytest -q` (99 tests), `python tools/run_test_scenarios.py`.

---

## Tools Required (skill side)

- **WebSearch** / **WebFetch** - live domain news, reports, standards updates
- **Read / Write** - read SECOND-KNOWLEDGE-BRAIN.md; append knowledge entries
- **Bash** - run `tools/knowledge_updater.py` for periodic crawl; run the engine + tests
- **Skill** - invoke sub-skills sequentially through the harness

---

## Knowledge Sources

### Domain Authoritative Sources
PostgreSQL & NoSQL design references, time-series/scoreboard references, game
analytics, replay/match-data schemas, GDPR/COPPA, OpenTelemetry/metrics.

### Academic & Research Sources
Proceedings of the VLDB Endowment, IEEE Transactions on Games, Information
Systems (Elsevier), Entertainment Computing (Elsevier), Journal of Systems and
Software (Elsevier), Computers in Human Behavior (Elsevier).

### Academic Crawl Targets
Semantic Scholar / Google Scholar keyword clusters, ArXiv categories
(cs.DB, cs.GT), domain preprint servers, standards bodies and professional
associations.

---

## Supporting Python Tools

| File | Purpose |
|------|---------|
| `indie_match_history/` | The production-grade engine package (models, ratings, storage, leaderboard, replay, privacy, engine, CLI). |
| `tools/knowledge_updater.py` | Crawl pipeline: fetches latest papers + news -> scores -> appends to SECOND-KNOWLEDGE-BRAIN.md. |
| `tools/run_test_scenarios.py` | Structural & content validator (8-File Contract + package layout + live smoke). |
| `tools/test_knowledge_updater.py` | Knowledge updater unit tests (hash, score, format, config). |

---

## Automated Knowledge Update Schedule

```cron
# Weekly academic update (Mondays 8:00 AM)
0 8 * * 1 python tools/knowledge_updater.py >> logs/knowledge_update.log 2>&1

# Daily news update (Daily 7:00 AM)
0 7 * * * python tools/knowledge_updater.py --news-only >> logs/knowledge_news.log 2>&1
```

Manual: `python tools/knowledge_updater.py --dry-run | --news-only | --keywords "..." | --list`

---

## Active Development Tasks

- [x] Phase 0: Architecture & source map
- [x] Phase 1: Core sub-skills (production-grade)
- [x] Phase 2: Main harness + 10 quality gates + graceful degradation
- [x] Phase 3: Knowledge pipeline + tests + cron
- [x] Phase 4: Testing & validation (99 tests + validator)
- [x] Phase 5: Integration & polish - PRODUCTION READY v1.1.0
  - [x] Real engine package `indie_match_history` (models, ratings, storage,
        leaderboard, replay, privacy, engine, CLI, schema migrations)
  - [x] Full pytest suite (99 tests) across all components
  - [x] Upgraded knowledge crawler (structured logging, Candidate dataclass,
        `--list`, safe regex)
  - [x] Upgraded validators asserting package layout + live smoke run
  - [x] Open-source artifacts: LICENSE, CHANGELOG, CONTRIBUTING, SECURITY,
        pyproject.toml

---

## References

- `PROJECT-detail.md` - full technical specification
- `PROJECT-DEVELOPMENT-PHASE-TRACKING.md` - build roadmap
- `SECOND-KNOWLEDGE-BRAIN.md` - self-improving knowledge base
- `D:\972026\SKILL-STANDARD.md` - library-wide standard
- Reference impl: `D:\vn-finance-analysis-hd-skill`