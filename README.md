# indie-game-match-history-database

**Historical Match Database Architecture & Engine for Indie Multiplayer Games**

[![Claude Skill](https://img.shields.io/badge/Claude-Skill-blue)](https://claude.ai/claude-code)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://img.shields.io/badge/tests-99%20passing-brightgreen)](#testing)

A production-grade, dependency-free Python engine plus a Claude Code analysis
harness for **Indie Game Match-History Data Engineering**. The engine
implements the storage, rating, leaderboard, replay, and privacy architecture
that the skill harness analyses and recommends - so the skill's output is
grounded in runnable, tested code rather than prose alone.

## Highlights
- **Typed data models** for players, matches, results, events, replays, ratings
  (immutable matches, JSON round-trippable).
- **Rating engines**: ELO (FIDE-style K ladder) and Glicko-2 (full Glickman 2012
  volatility iteration), both pure and deterministic.
- **Pluggable storage backends**: in-memory, durable SQLite (auto-migrating,
  parameterized queries), and a tiered wrapper modelling hot/warm/cold tiers.
- **ZSET-style leaderboards** in pure Python (bisect-backed, deterministic
  tie-breaks) - the same semantics competitive games rely on from Redis.
- **Replay blob store**: content-addressed, gzip-compressed, SHA-256 integrity
  verified, with a configurable size ceiling and magic-byte guard.
- **GDPR/COPPA privacy pipeline**: retention aging, replay expiry, and
  right-to-erasure (hard-delete for 1v1, anonymization for team matches).
- **Structured JSON logging** and a typed error hierarchy.
- **`imh` CLI** for ops, CI smoke tests, and local development.
- **Claude Code skill harness**: 5 sub-skills, 10 quality gates, graceful
  degradation, and a self-improving academic knowledge base.

## Installation
```bash
pip install -e .                 # core engine (pure stdlib)
pip install -e ".[all]"           # + crawl deps + dev/test extras
```
The core engine has **zero runtime dependencies**. The optional `crawl` extra
(`requests`, `feedparser`, `python-dateutil`) is only needed to run the
knowledge-base crawler. Skill markdown files install to `~/.claude/skills/` or
are used via the project `CLAUDE.md`.

## Quick start
```python
from indie_match_history import (
    MatchHistoryEngine, MatchResult, MatchOutcome,
)

with MatchHistoryEngine() as eng:           # in-memory + ELO by default
    alice = eng.register_player("alice")
    bob   = eng.register_player("bob")
    res = eng.record_match(
        "pong",
        [MatchResult(alice.player_id, MatchOutcome.WIN),
         MatchResult(bob.player_id,   MatchOutcome.LOSS)],
        season="s1",
    )
    print(res.rating_deltas)                # {'<alice>': (1200.0, 1220.0), ...}
    print([e.member for e in eng.leaderboard("pong", "s1", top=5)])
```

Durable SQLite + Glicko-2 + replays:
```python
from indie_match_history import EngineConfig, MatchHistoryEngine
cfg = EngineConfig(rating_system="glicko2",
                   sqlite_path="matches.db", replay_root="./replays")
with MatchHistoryEngine(config=cfg) as eng:
    ...
    eng.attach_replay(match_id, blob_bytes)
    eng.run_retention()                     # age tiers + expire old replays
    eng.erase_player(player_id)             # GDPR/COPPA erasure
```

## CLI
```bash
imh --db matches.db player-add --handle alice
imh --db matches.db match-add --spec match.json
imh --db matches.db --replay-root ./replays replay-attach --match-id <id> --file replay.bin
imh --db matches.db leaderboard --game-id pong --season s1 --top 10
imh --db matches.db retention
imh --db matches.db erase --player-id <id>
imh --db matches.db stats
```
`match.json` schema:
```json
{
  "game_id": "pong", "season": "s1", "mode": "ranked",
  "results": [
    {"player_id": "<id>", "outcome": "win"},
    {"player_id": "<id>", "outcome": "loss"}
  ]
}
```

## Architecture
```
USER / SERVER
   |
   v
MatchHistoryEngine  (facade)
   |--- ratings.py        ELO / Glicko-2  (pure)
   |--- leaderboard.py    ZSET-style sorted set
   |--- replay.py         blob store (gzip + sha256)
   |--- privacy.py        retention + erasure pipeline
   |--- storage/          base | memory | sqlite | tiered(hot/warm/cold)
   |--- schema.py         versioned migrations (v1->v3)
   |--- models.py         immutable typed records
   |--- cli.py            imh
```
The Claude Code skill harness (`skills/*.md`) provides the analysis &
decision-support workflow that recommends how to deploy and tune this engine.
See `PROJECT-detail.md` for the harness flow and `skills/main.md` for the
6-step protocol + 10 quality gates.

## Quality Gates
Universal gates U1-U6 plus domain gates defined in `skills/main.md`:
- **G1** data model & storage tiering defined
- **G2** query patterns & indexes designed
- **G3** scalability (sharding/caching) addressed
- **G4** privacy/retention (GDPR/COPPA) addressed

## Testing
```bash
pytest -q                          # 99 unit + integration tests
python tools/run_test_scenarios.py # structural & content validator
python tools/test_knowledge_updater.py
```

## Knowledge Base
`SECOND-KNOWLEDGE-BRAIN.md` is a living, auto-updated knowledge base. The crawl
pipeline (`tools/knowledge_updater.py`) fetches from ArXiv, Semantic Scholar,
and RSS, dedupes by SHA-256 of DOI/URL, scores by recency + relevance +
citations, and appends the top-N. Schedule (see `CLAUDE.md`): weekly academic
+ daily news.

```bash
python tools/knowledge_updater.py --dry-run
python tools/knowledge_updater.py --list
```

## Data Sources
PostgreSQL & NoSQL design references, time-series/scoreboard references, game
analytics, replay/match-data schemas, GDPR/COPPA, OpenTelemetry, and academic
venues (PVLDB, IEEE Trans. Games, Information Systems, Entertainment
Computing, JSS, Computers in Human Behavior).

## Roadmap
- [x] Phase 0: Architecture & source map
- [x] Phase 1: Core sub-skills (5)
- [x] Phase 2: Main harness + 10 quality gates + degradation
- [x] Phase 3: Knowledge pipeline + tests + cron
- [x] Phase 4: Testing & validation (99 tests + validator)
- [x] Phase 5: Integration & polish - PRODUCTION READY v1.1.0

## License
MIT - see [LICENSE](LICENSE).

## Citation
```bibtex
@software{indie-game-match-history-database,
  title  = {indie-game-match-history-database: Historical Match Database
            Architecture & Engine for Indie Games},
  year   = {2026},
  version= {1.1.0}
}
```

## Why This Skill
Indie Game Match-History Data Engineering practitioners face fragmented data,
inconsistent methodology, and tools that do not self-improve. This project
unifies a runnable, tested engine with an evidence-backed, self-improving
analysis harness - so recommendations are grounded in code that actually
compiles and passes tests.