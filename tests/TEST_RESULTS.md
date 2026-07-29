# TEST_RESULTS.md - Skill 263: indie-game-match-history-database

## Validation Summary

| Suite | Checks | Passed | Result |
|-------|--------|--------|--------|
| `pytest` (engine package) | 99 tests | 99 | PASS |
| `tools/test_knowledge_updater.py` | hash, score, format, config | 4 | PASS |
| `tools/run_test_scenarios.py` (8-File Contract + package layout + live smoke) | full suite | all | PASS |

**Overall: PRODUCTION READY v1.1.0 - all validators pass.**

## Engine test breakdown (99 tests)

| Module | Coverage |
|--------|----------|
| `tests/test_models.py` | typed models, validation, JSON round-trips, immutability |
| `tests/test_ratings.py` | ELO expected-score, K ladder, zero-sum, forfeit; Glicko-2 direction, RD shrink, factory |
| `tests/test_storage.py` | in-memory + SQLite: upsert/conflict, match insert/dup, filters, events, ratings (incl. NULL match seed), tiering, purge (1v1 drop + team anonymize), schema migration/downgrade |
| `tests/test_leaderboard.py` | ZSET add/top/incr_by/rank/around/remove_range, tie-break, errors, round-trip |
| `tests/test_replay.py` | store/load round-trip, gzip compression, magic guard, size ceiling, corruption detection, delete |
| `tests/test_privacy.py` | tier-for-age, tier promotion, replay expiry, erasure (1v1 + minor hard-delete), policy validation |
| `tests/test_engine.py` | rating+leaderboard update, unregistered rejection, casual skip, history, replay attach/link, stats, glicko2 E2E, config validation |
| `tests/test_cli.py` | player/match/leaderboard/rating/history/replay-attach/erase/retention/stats CLI flows |
| `tests/test_schema.py` | fresh migration, idempotency, downgrade rejection, partial target |

Storage and engine tests are parametrized across **in-memory** and **SQLite**
backends so the contract holds for both the test/small-game path and the
durable default.

## Skill harness validation (`tools/run_test_scenarios.py`)
- 8-File Contract: all required harness + open-source files present.
- Sub-skill set exact match (5 sub-skills); frontmatter + mandatory sections.
- `main.md`: 10 quality gates (U1-U6 + G1-G4), Pre-Flight language detection,
  graceful degradation, limitation banner, output template.
- `SECOND-KNOWLEDGE-BRAIN.md`: evidence hierarchy tiers, >=4 DOI-cited
  references, data sources + self-update protocol sections.
- `tests/test-scenarios.md`: >=5 scenarios incl. degraded + comparison cases.
- Engine package: 17 module files present; full public API surface importable;
  live smoke run (register -> match -> leaderboard) succeeds.

## Test scenario coverage (`tests/test-scenarios.md`)

`tests/test-scenarios.md` defines 5 end-to-end scenarios covering:
- a standard/object analysis case,
- a minimal-input / default case,
- a comparison case,
- a risk/feasibility or conflict case,
- a degraded-mode case (missing input / unreachable sources) with a LIMITATION notice.

All universal gates U1-U6 and all domain gates (G1, G2, G3, G4) are exercised
across the scenarios. All verdict categories (Scalable Schema, Conditional
(scale), Unscalable/Non-private, Inconclusive) are covered.

## Reproduction
```bash
pip install -e ".[all]"
pytest -q
python tools/run_test_scenarios.py
python tools/test_knowledge_updater.py
python tools/knowledge_updater.py --dry-run
python tools/knowledge_updater.py --list
```