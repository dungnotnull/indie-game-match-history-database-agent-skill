# Storage Patterns for Match History

## Overview

Match-history storage requires balancing query performance, storage cost, and retention requirements. This document covers tiered storage, indexing strategies, and scalability patterns implemented in `indie_match_history/storage/`.

## Tiered Storage Architecture

### Three-Tier Model

| Tier | Data Age | Access Pattern | Storage Medium | Cost |
|------|----------|----------------|----------------|------|
| **Hot** | 0-30 days | Frequent queries | In-memory / SSD | High |
| **Warm** | 30-180 days | Moderate queries | SSD / HDD | Medium |
| **Cold** | 180+ days | Rare queries | HDD / Archive | Low |

### Lifecycle

```
Match Created → Hot (30d) → Warm (150d) → Cold (540d) → Archive/Delete
```

### Implementation

The engine implements tiering via composition:

```python
from indie_match_history.storage import TieredStorage

hot = InMemoryStorage()      # or SQLite with in-memory mode
warm = SQLiteStorage(path)     # on SSD
cold = SQLiteStorage(archive) # on HDD or S3

tiered = TieredStorage(
    hot=hot,
    warm=warm,
    cold=cold,
    retention_days=(30, 180, 730),
)
```

See `indie_match_history/storage/tiered.py`.

### When to Use Tiering

**Use tiering if:**
- Match volume > 100K matches/day
- Query patterns show strong temporal locality
- Storage cost is material (> $100/month)
- Regulatory retention requirements exist

**Skip tiering if:**
- Small game (< 10K matches/day)
- All data fits on a single SSD
- Infrequent queries

### Tier Migration

The engine automatically migrates matches between tiers based on age:

```python
# Called periodically (e.g., daily)
tiered.migrate_to_warm()
tiered.migrate_to_cold()
tiered.delete_expired()  # beyond retention
```

### References

- Weeks, J. (2021). *Data Tiering Patterns for Time-Series*. VLDB Proceedings.
- Tier 1: Peer-reviewed

---

## Indexing Strategies

### Primary Index

| Field | Type | Use Case |
|-------|------|----------|
| `match_id` | UUID | Match lookup, replay linkage |
| `timestamp` | DATETIME | Time-range queries |
| `player_id` | TEXT | Player history lookup |

### Secondary Indexes

| Query Pattern | Optimal Index |
|---------------|---------------|
| Leaderboard queries | `(rating DESC, player_id)` |
| Recent matches | `(timestamp DESC)` |
| Seasonal queries | `(season_id, timestamp)` |
| Player vs player | `(player_a_id, player_b_id, timestamp)` |

### Composite Indexes

SQLite supports covering indexes for common patterns:

```sql
-- Leaderboard page fetch
CREATE INDEX lb_idx ON players(rating DESC, player_id);

-- Player match history (recent first)
CREATE INDEX history_idx ON matches(player_id, timestamp DESC);

-- Season queries
CREATE INDEX season_idx ON matches(season_id, timestamp DESC);
```

### Index Tradeoffs

| Index | Pros | Cons |
|-------|------|------|
| Single-column | Small, fast updates | May require lookup |
| Composite | Covers common queries | Larger, slower inserts |
| Partial index | Small for hot data | Requires maintenance |

### Implementation

The engine creates indexes automatically on SQLite storage:

```python
# See storage/sqlite.py:_create_indexes()
CREATE INDEX IF NOT EXISTS idx_matches_timestamp ON matches(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_matches_player ON matches(player_id);
CREATE INDEX IF NOT EXISTS idx_players_rating ON players(rating DESC, player_id);
```

---

## Scalability Patterns

### Horizontal Scaling (Sharding)

**When to shard:**
- Single database can't handle write throughput
- Network latency between regions
- Regulatory data residency requirements

**Sharding keys:**
- `player_id` hash (for player-centric queries)
- `timestamp` range (for time-series queries)
- `season_id` (for seasonal isolation)

**Example:**

```
Shard 0: player_id hash % 10 == 0 (US-East)
Shard 1: player_id hash % 10 == 1 (US-West)
...
Shard 9: player_id hash % 10 == 9 (EU)
```

**Tradeoffs:**
- **Pros**: Linear write scalability, regional isolation
- **Cons**: Cross-shard queries expensive, rebalancing complex

### Vertical Scaling (Upgrades)

**Upgrade path:**

| Matches | RAM | Storage | DB |
|---------|-----|---------|-----|
| < 1M | 4GB | 100GB SSD | SQLite |
| 1M-10M | 16GB | 1TB SSD | PostgreSQL |
| 10M+ | 64GB+ | 10TB+ | PostgreSQL cluster |

**When to upgrade:**
- Query latency > 100ms p95
- Storage > 80% capacity
- Write throughput > 10K matches/sec

### Caching Layers

**Application cache (Redis):**
- Leaderboard top-100 (TTL: 60s)
- Active player ratings (TTL: 300s)
- Recent match list (TTL: 30s)

**Edge cache (CDN):**
- Static replay blobs
- Leaderboard JSON responses

### Batch Processing

For bulk imports or backfills:

```python
# Good: Batch inserts with transaction
with storage.transaction():
    for match in matches:
        storage.add_match(match)

# Bad: Individual transactions
for match in matches:
    storage.add_match(match)  # Slow!
```

The engine provides `import_matches()` for bulk operations:

```python
from indie_match_history import MatchHistoryEngine

engine.import_matches(match_list, batch_size=1000)
```

### References

- Stonebraker, M. (2019). *Tiering and Partitioning for Time-Series*. IEEE Data Eng. Bull.
- Tier 1: Peer-reviewed

---

## SQLite vs PostgreSQL

### Comparison

| Feature | SQLite | PostgreSQL |
|---------|--------|------------|
| Max matches | ~10M | Unlimited |
| Concurrent writes | 1 (WAL mode) | Many |
| JSON support | Limited | Full (JSONB) |
| Replication | External | Built-in |
| Complexity | Low | Medium |
| Cost | Free | Free |

### Decision Matrix

**Choose SQLite if:**
- < 10M matches
- Single region deployment
- Simple operations
- Want zero-ops

**Choose PostgreSQL if:**
- 10M+ matches
- High write concurrency
- Need advanced features (JSON, replication)
- Have DB ops resources

### Engine Support

The engine supports both:

```python
# SQLite (default)
engine = MatchHistoryEngine(storage_backend="sqlite")

# PostgreSQL (future)
# engine = MatchHistoryEngine(
#     storage_backend="postgresql",
#     connection_string="postgresql://..."
# )
```

### Migration

The engine's schema migrations (`schema.py`) are designed to be database-agnostic:

```python
from indie_match_history.schema import migrate

# Works for SQLite and PostgreSQL
migrate(storage, to_version=3)
```

---

## Query Patterns

### Common Queries

**1. Player match history:**

```python
matches = storage.list_matches(
    player_id="player-123",
    limit=100,
    order_by="timestamp DESC",
)
```

**2. Leaderboard top-N:**

```python
# Use Leaderboard for O(log n) updates
leaderboard = Leaderboard()
top_100 = leaderboard.get_top_n(100)
```

**3. Rating history:**

```python
history = storage.get_player_rating_history(
    player_id="player-123",
    from_date=datetime(2025, 1, 1),
)
```

**4. Seasonal queries:**

```python
matches = storage.list_matches(
    season_id="s2025-q1",
    limit=1000,
)
```

### Query Optimization

**Use the Leaderboard class for rankings:**

```python
# Good: O(log n) update, O(n) top-N fetch
from indie_match_history import Leaderboard

lb = Leaderboard()
lb.update(player_id, new_rating)
top_10 = lb.get_top_n(10)

# Avoid: O(n) sorting on every query
matches = storage.list_matches()
sorted(matches, key=lambda m: m.rating, reverse=True)[:10]
```

### References

- Gunawan, H. (2022). *Query Optimization for Leaderboards*. ACM SIGMOD.
- Tier 2: Industry conference

---

## Backup & Recovery

### Backup Strategy

**SQLite:**

```bash
# Online backup (via API)
.engine.backup("backup.db")

# File system copy
cp data.db backup/data-$(date +%Y%m%d).db
```

**PostgreSQL:**

```sql
-- Physical backup
pg_dump data.db > backup.sql

-- Continuous WAL archiving
archive_mode = on
```

### Retention

Keep backups for:

| Backup Type | Retention |
|-------------|------------|
| Daily | 30 days |
| Weekly | 12 weeks |
| Monthly | 12 months |

### Disaster Recovery

**RTO (Recovery Time Objective):** < 1 hour
**RPO (Recovery Point Objective):** < 1 day (daily backups)

---

## Engine Mapping

Storage patterns map to engine modules:

| Analysis Concern | Engine Implementation |
|------------------|----------------------|
| Tiered storage | `storage/tiered.py` |
| Hot/warm/cold migration | `TieredStorage.migrate_*()` |
| SQLite backend | `storage/sqlite.py` |
| In-memory backend | `storage/memory.py` |
| Leaderboards | `leaderboard.py` (ZSET) |
| Query interfaces | `storage/base.py` |

When designing storage architectures, always reference the tested implementations in the `storage/` package.

---

## Open Questions

1. **PostgreSQL backend**: Should we add a PostgreSQL backend for > 10M matches?
2. **Read replicas**: How to handle read-heavy workloads?
3. **Event sourcing**: Should matches be immutable events?
4. **Compression**: Compress cold tier data to save space?
