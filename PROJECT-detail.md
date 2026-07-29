# PROJECT-detail.md - Skill 263: indie-game-match-history-database

## Executive Summary

`indie-game-match-history-database` is a professional-grade harness for Claude
Code targeting the **Indie Game Match-History Data Engineering** domain. It
transforms Claude into a domain expert that delivers structured, evidence-backed
outputs by combining real-time data aggregation, recognized domain methods,
and academic research into a single orchestrated workflow ending in a
risk/limitation-disclosed recommendation.

Unlike pure-prose skills, the analysis is grounded in a runnable, tested engine
package (`indie_match_history/`) that implements the very storage, rating,
leaderboard, replay, and privacy architecture the skill recommends.

---

## Problem Statement

Practitioners in this domain face three structural gaps:
1. **Data fragmentation** - authoritative data is scattered across sources.
2. **Methodology gaps** - most advice lacks systematic, evidence-graded methods.
3. **No self-improvement** - static tools do not learn from new research.

This skill addresses all three via real-time aggregation, professional
frameworks, a continuously-updated knowledge crawl pipeline, and a real engine.

---

## Target Users & Use Cases

| User | Trigger Example | Skill Response |
|------|----------------|----------------|
| Practitioner | "Design match-history storage for game X at 10M matches/day" | Evidenced architecture report grounded in the engine's capabilities |
| Researcher | "Which rating system fits a small FFA indie game?" | Method-grounded guidance (ELO vs Glicko-2) with citations |
| Decision-maker | "Assess privacy/retention risk for minors" | Risk-disclosed GDPR/COPPA assessment tied to `PrivacyPipeline` |
| Learner | "Explain ZSET-style leaderboards in this domain" | Educational framing with the `Leaderboard` reference impl |

---

## Harness Architecture

```
USER INPUT
    |
    v
[main.md - indie-game-match-history-database]
    |
    +--> sub-gather-requirements.md  -> structured requirements
    +--> sub-evidence-collector.md   -> evidence bundle
    +--> sub-core-analysis.md        -> storage architecture scorecard
    +--> sub-knowledge-updater.md    -> academic evidence + gap flags
    +--> sub-advisor.md              -> risk-disclosed conclusion + actions
    |
    +--> [QUALITY GATE - main.md]
            OK claims cited, disclosure present, hierarchy respected,
            output formatted per template
```

The engine package maps 1:1 to the analysis concerns:

| Analysis concern | Engine implementation |
|------------------|------------------------|
| Data model | `models.py` (Player, Match, MatchResult, MatchEvent, ReplayRef, Rating) |
| Rating systems | `ratings.py` (EloEngine, Glicko2Engine) |
| Storage tiering | `storage/tiered.py` + `storage/sqlite.py` (hot/warm/cold) |
| Query patterns | `storage/base.py` (list_matches, player_history, season filters) |
| Leaderboards | `leaderboard.py` (ZSET-style sorted set) |
| Replay storage | `replay.py` (gzip + SHA-256 + content-addressed) |
| Privacy/retention | `privacy.py` (retention aging, replay expiry, erasure) |
| Schema evolution | `schema.py` (versioned migrations v1->v3) |
| Orchestration | `engine.py` (MatchHistoryEngine facade) |
| Operations | `cli.py` (`imh`) |

---

## Full Sub-Skill Catalog

### 1. `sub-gather-requirements.md`
- **Purpose:** Clarify object of analysis, constraints, timeframe, available
  inputs, target audience, language before any data fetching.
- **Role:** intake specialist.
- **Inputs:** Raw user message + any provided materials.
- **Outputs:** `{object, scope, timeframe, available_inputs, target_audience, language, analysis_type}`.
- **Tools:** Conversation only.
- **Quality Gate:** At least one object of analysis confirmed before proceeding.

### 2. `sub-evidence-collector.md`
- **Purpose:** Fetch authoritative real-time and reference data: status/
  parameters, docs/standards, recent developments, reference benchmarks.
- **Role:** data librarian.
- **Inputs:** Requirements object from Step 1.
- **Outputs:** `{current_data, authoritative_docs, recent_news, reference_benchmarks}` with source + date per item.
- **Tools:** WebSearch, WebFetch, Read (SECOND-KNOWLEDGE-BRAIN.md).
- **Quality Gate:** At least current data + 1 authoritative document, or a limitation flag.

### 3. `sub-core-analysis.md`
- **Purpose:** Design historical match-data storage: data model, tiering,
  query patterns/indexes, scalability, replay storage, privacy/retention.
- **Role:** match-history data engineer.
- **Inputs:** Game, expected player/match volume, leaderboards, language.
- **Outputs:** Data model + tiering + query/index + scalability + replay + privacy + best/base/worst scale scenarios.
- **Tools:** Read (SECOND-KNOWLEDGE-BRAIN.md), WebFetch, reasoning. Reference the engine package as the concrete implementation.
- **Quality Gate:** Data model & tiering defined; query patterns/indexes designed; privacy/retention addressed.

### 4. `sub-knowledge-updater.md`
- **Purpose:** Query SECOND-KNOWLEDGE-BRAIN.md for authoritative academic and
  professional evidence; surface citations with Tier labels; flag gaps.
- **Role:** research librarian.
- **Inputs:** Topic keywords from the current analysis.
- **Outputs:** 3-5 knowledge-base citations with Tier labels + flagged gaps.
- **Tools:** Read (SECOND-KNOWLEDGE-BRAIN.md), WebSearch (gap-fill, max 2).
- **Quality Gate:** At least 1 academic/authoritative source surfaced; coverage rating provided.

### 5. `sub-advisor.md`
- **Purpose:** Synthesize all prior analysis into a risk-disclosed conclusion
  with a full evidence chain and recommended actions.
- **Role:** senior advisor.
- **Inputs:** Core analysis scorecard + evidence bundle + knowledge-base evidence.
- **Outputs:** Conclusion (one of N declared categories) + scenarios + key risks + evidence chain + remediation + disclosure.
- **Quality Gate:** Conclusion is exactly one of: Scalable Schema / Conditional (scale) / Unscalable/Non-private / Inconclusive; disclosure appears before the conclusion.

---

## Skill File Format Specification

```markdown
---
name: {skill-name}
description: {one-line summary}
---
## Role & Persona
## Workflow (Harness Flow)
## Sub-skills Available   (main.md only)
## Tools
## Output Format
## Quality Gates
```

---

## E2E Execution Flow

```
1. User invokes /indie-game-match-history-database [query]
2. main.md -> sub-gather-requirements -> structured requirements
3. sub-evidence-collector -> data bundle
4. sub-core-analysis -> storage architecture scorecard
5. sub-knowledge-updater -> academic evidence entries
6. sub-advisor -> final draft
7. main.md Quality Gate -> verify, auto-fix, deliver
```

**Error handling:** primary sources fail -> fallback chain -> knowledge base ->
explicit limitation flag; never silently proceed with stale data.

---

## SECOND-KNOWLEDGE-BRAIN Integration

- **Sources crawled:** academic databases (ArXiv cs.DB/cs.GT, Semantic Scholar)
  + domain RSS + standards docs.
- **Crawl config:** `KNOWLEDGE_CONFIG` in `tools/knowledge_updater.py`.
- **Dedup:** SHA-256 of DOI/URL (case/whitespace-insensitive).
- **Scoring:** recency(0.4) + keyword_relevance(0.4) + citation_count(0.2) -> 0-10.

---

## Quality Gates Definition

Universal gates U1-U6 (see library SKILL-STANDARD.md) plus the domain gates
defined in `skills/main.md`: G1 (data model & tiering), G2 (queries & indexes),
G3 (scalability), G4 (privacy/retention).

---

## Test Scenarios

See `tests/test-scenarios.md` for 5+ concrete scenario tests, and `tests/` for
the full pytest suite (99 unit + integration tests) covering models, ratings,
storage, leaderboard, replay, privacy, engine, CLI, and schema migrations.

---

## Key Design Decisions

1. Domain sub-skills kept separate (distinct methods/data), analysis grounded in
   a real engine package.
2. Authoritative domain sources as primary; global fallback secondary.
3. Disclosure enforced at the quality-gate level, not optional.
4. SECOND-KNOWLEDGE-BRAIN as living memory updated by the crawl pipeline.
5. Graceful degradation to knowledge base with explicit limitation flags.
6. Matches are immutable once stored; replay linkage is the only post-creation
   mutation (via `link_replay`).
7. Rating engines are pure & deterministic so they can be unit-tested in
   isolation and reused by any backend.
8. SQLite backend is the durable default; in-memory for tests/small games;
   tiering is a composition wrapper, not a separate store.

---

## Idea (Vietnamese)

> Tao skill thiet ke va toi uu hoa cau truc co so du lieu luu tru lich su dau
> cho cac tua game indie da nguoi choi, viec danh gia va dua de xuat phai dua
> tren cac phuong phap danh gia uy tin tren the gioi va dua ra cac de xuat,
> giai phap cai tien, khong ngung di crawl data tu cac kien truc he thong du
> lieu lon hoac document uy tin lien quan de cap nhat kien thuc cho skill
> ngay cang tot hon, xu huong hon. Ky nien thuc do duoc grounding vao mot
> engine Python thuc te, da duoc test, de cac de xuat co the chay duoc.