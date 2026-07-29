# test-scenarios.md - Skill 263: indie-game-match-history-database

Five concrete end-to-end scenarios for the analysis harness. Each lists inputs,
expected steps, and applicable quality gates. The scenarios exercise all
universal gates U1-U6 and the domain gates G1, G2, G3, G4, plus all verdict
categories. Concrete behavioural assertions for the backing engine live in the
`tests/` pytest suite (99 tests).

---

## Scenario 1: Standard analysis (object in scope)
- **Input:** a typical Indie Game Match-History Data Engineering case with
  complete inputs (game, expected match volume, leaderboards, language).
- **Expected:** sub-gather-requirements -> sub-evidence-collector ->
  sub-core-analysis -> sub-knowledge-updater -> sub-advisor -> quality gate.
  The core-analysis step should reference the `indie_match_history` engine
  modules (models, storage/tiered, leaderboard, replay, privacy).
- **Gates:** U1-U6 + G1, G2, G3, G4.
- **Verdict target:** Scalable Schema.
- **Engine mapping:** `MatchHistoryEngine.record_match` -> `leaderboard` ->
  `replay.attach_replay` all succeed; tiering stays HOT.

## Scenario 2: Minimal-input analysis (defaults)
- **Input:** terse request with minimal data (e.g. "design match storage for a
  small 2-player indie game").
- **Expected:** defaults applied with explicit assumption statement; never
  fabricate missing values. Default rating system ELO, in-memory or SQLite
  backend, default retention windows.
- **Gates:** U1-U6 + G1-G4.
- **Verdict target:** Conditional (scale).
- **Engine mapping:** `EngineConfig` defaults; `require_minimum_results` = 1.

## Scenario 3: Comparison scenario
- **Input:** compare two rating systems (ELO vs Glicko-2) or two backends
  (in-memory vs SQLite) for a given scale.
- **Expected:** side-by-side scorecard + evidence-based winner; sub-core-analysis
  applied to both. Reference `EloEngine` / `Glicko2Engine` and `InMemoryStorage`
  / `SQLiteStorage` concretely.
- **Gates:** U3 (evidence hierarchy), U6, G1, G2.
- **Verdict target:** Conditional (scale).

## Scenario 4: Risk / feasibility or conflict scenario
- **Input:** assess privacy/retention risk for a minors-facing game, or resolve
  conflicting scale vs. privacy signals.
- **Expected:** multi-scenario (best/base/worst) risk output with stated
  precedence where conflicts exist. Reference `PrivacyPipeline`,
  `RetentionPolicy.minors_force_delete`, and `purge_player_data` semantics
  (1v1 hard-delete, team anonymization).
- **Gates:** U2 (disclosure), G1, G2, G3, G4.
- **Verdict target:** Unscalable/Non-private (if retention cannot be honored) or
  Conditional (scale).

## Scenario 5: Degraded-mode scenario
- **Input:** primary sources unreachable OR a required input variable missing
  (e.g. player unregistered, replay blob corrupt).
- **Expected:** fallback chain + LIMITATION notice (degradation Level 2-3); no
  fabricated values; verdict maps to Inconclusive when the missing input is
  decisive. Engine raises typed errors (`NotFoundError`, `ReplayError`,
  `ValidationError`) instead of producing silent garbage.
- **Gates:** U2, graceful-degradation levels 0-4, G1, G2, G3, G4.
- **Verdict target:** Inconclusive.

### Gate coverage matrix

| Gate | S1 | S2 | S3 | S4 | S5 |
|------|----|----|----|----|----|
| G1 | Y | Y | Y | Y | Y |
| G2 | Y | Y | Y | Y | Y |
| G3 | Y | Y | Y | Y | Y |
| G4 | Y | Y | Y | Y | Y |
| U1-U6 | Y | Y | Y | Y | Y |

### Verdict coverage
Scalable Schema, Conditional (scale), Unscalable/Non-private, Inconclusive.