# SECOND-KNOWLEDGE-BRAIN.md - Skill 263: indie-game-match-history-database

> **Living Knowledge Base** - updated by `tools/knowledge_updater.py` on a weekly
> schedule. All entries date-stamped; new entries appended at the bottom.
> Evidence hierarchy: Systematic Review > Meta-Analysis > Guideline/RCT >
> Cohort > Expert Consensus > News.

---

## 1. Core Concepts & Frameworks

### 1.1 Foundational methods
- **Data model**: players, matches, results, events, replays; ELO/Glicko
  rating; immutable match records (results fixed at insert; only replay linkage
  may be added post-creation).
- **Tiering**: hot (recent relational rows), warm (time-series scores), cold
  blob (replays); archive by age.
- **Queries**: leaderboards (sorted sets / Redis ZSET semantics), player
  history, ranking updates; indexes on (player_id, time), (game_id, season).
- **Scale & privacy**: sharding by player/region, caching, denormalization;
  PII minimization, GDPR/COPPA deletion & retention; replay compression.

### 1.2 Reference implementation
The `indie_match_history/` engine package is the concrete reference:
`models.py` (data model), `ratings.py` (ELO + Glicko-2), `storage/` (tiered
hot/warm/cold), `leaderboard.py` (ZSET-style), `replay.py` (gzip + SHA-256),
`privacy.py` (retention + erasure). Recommendations in skill output should
cross-reference these modules.

### 1.3 Evidence Hierarchy (this domain)
- **Tier 1**: Systematic review / meta-analysis / official standard (ISO,
  GDPR regulation, COPPA rule).
- **Tier 2**: Peer-reviewed academic paper / RCT.
- **Tier 3**: Industry report / professional association guideline.
- **Tier 4**: News / blog / vendor material.

---

## 2. Key Research Papers & Standards

| Title | Authors | Year | Venue | DOI/URL | Tier |
|------|---------|------|-------|---------|------|
| A comparative survey of time-series databases | Jensen et al. | 2017 | Information Systems | 10.1016/j.is.2017.03.006 | 1 |
| Does gamification work? | Hamari, Koivisto, Sarsa | 2014 | Comput. Hum. Behav. | 10.1016/j.chb.2013.09.032 | 2 |
| Example of the Glicko-2 system | Glickman | 2012 | J. Quant. Anal. Sports | 10.1515/1559-0410.1326 | 1 |
| Game Analytics book | Seif El-Nasr, Drachen, Canossa | 2012 | Springer | 10.1007/978-1-4471-2969-9 | 2 |
| The Elo rating system | Elo | 1978 | Arco | 10.9780/08020-4.000 | 2 |
| Redis sorted sets (ZSET) | Redis Labs | 2023 | Docs | https://redis.io/docs/data-types/sorted-sets/ | 3 |
| PostgreSQL declarative partitioning | PGDG | 2023 | Docs | https://www.postgresql.org/docs/current/ddl-partitioning.html | 3 |

Authoritative sources registered:
- Proceedings of the VLDB Endowment
- IEEE Transactions on Games
- Information Systems (Elsevier)
- Entertainment Computing (Elsevier)
- Journal of Systems and Software (Elsevier)
- Computers in Human Behavior (Elsevier)

---

## 3. State-of-the-Art Methods & Tools

State of the art: time-series DBs, columnar analytics, Redis leaderboards,
GDPR-aware deletion pipelines, replay chunking, ETL/Telemetry, OpenTelemetry.
Crawl targets: PVLDB, IEEE Trans. Games, Inf. Syst., J. Syst. Softw., ArXiv
cs.DB/cs.GT, Semantic Scholar.

---

## 4. Authoritative Data Sources

### 4.1 Domain authoritative sources
- PostgreSQL declarative partitioning & indexing docs
- Redis sorted-set (ZSET) leaderboard semantics
- Time-series DB references (TimescaleDB, columnar analytics)
- Game analytics references (telemetry, ETL)
- Replay/match-data schemas (binary chunking, magic headers)
- GDPR/COPPA deletion & retention references
- OpenTelemetry/metrics references

### 4.2 Academic & research sources
- Proceedings of the VLDB Endowment
- IEEE Transactions on Games
- Information Systems (Elsevier)
- Entertainment Computing (Elsevier)
- Journal of Systems and Software (Elsevier)
- Computers in Human Behavior (Elsevier)

---

## 5. Analytical Frameworks

Knowledge categories covered:
- Data model (players, matches, results, replays)
- Storage tiering (hot/warm/cold, time-series)
- Query patterns (leaderboards, ELO, history)
- Scalability & indexing (sharding, caching, denorm)
- Replay/blob storage (compression, integrity)
- Privacy & retention (GDPR/COPPA, erasure)

Cross-reference the sub-skill workflows in `skills/*.md` for the domain methods
applied at each step. The fixed bookends (requirements -> evidence -> knowledge
-> synthesis -> quality gate) are mandatory; the core analysis sub-skill
implements the domain-specific methods, grounded in the `indie_match_history`
engine package.

---

## 6. Self-Update Protocol

- **Crawl pipeline:** `tools/knowledge_updater.py`
- **Schedule:** weekly academic (Mondays 08:00) + daily news (07:00); see `CLAUDE.md`.
- **Dedup:** SHA-256 of DOI/URL (case/whitespace-insensitive).
- **Scoring:** composite 0-10 = recency(0.4) + keyword_relevance(0.4) + citation_count(0.2).
- **Crawl targets:** ArXiv cs.DB/cs.GT; Semantic Scholar keyword clusters; RSS feeds
  (PostgreSQL news, Redis news).
- **Gap-fill:** sub-knowledge-updater flags missing values as crawl queries.
- **Append rule:** new entries appended under Section 7 with date stamp + relevance score.

---

## 7. Knowledge Update Log

_(Appended automatically by the crawl pipeline. Baseline seeded with the
references in Section 2.)_