# Rating Systems for Indie Games

## Overview

Rating systems estimate player skill from match outcomes. This document compares the major systems implemented in `indie_match_history/ratings.py`.

## Systems Comparison

| System | Era | Complexity | Use Case | Implementation |
|--------|-----|------------|----------|----------------|
| **ELO** | 1960s | Low | Zero-sum 1v1 | `EloEngine` |
| **Glicko-1** | 1990s | Medium | Adds rating deviation | — |
| **Glicko-2** | 2012 | High | Adds volatility, time decay | `Glicko2Engine` |
| **TrueSkill** | 2005-2008 | High | Teams, factor graph | — |

## ELO System

### Description

Original chess rating system by Arpad Elo (1960s). Simple, widely adopted.

### Formula

```
Expected score A vs B:
E_A = 1 / (1 + 10^((R_B - R_A) / 400))

Rating update:
R'_A = R_A + K * (S_A - E_A)
```

Where:
- `R_A`, `R_B` = current ratings
- `S_A` = actual score (1=win, 0.5=draw, 0=loss)
- `K` = K-factor (max rating change per match)

### K-Factor Ladder

Our implementation uses FIDE-style K ladder:

| Matches Played | K-Factor |
|----------------|----------|
| < 30 | 40 |
| 30+ (rating < 2400) | 20 |
| 2400+ | 10 |

### Pros/Cons

**Pros:**
- Simple to implement and explain
- Computationally cheap (O(1) per update)
- Battle-tested (chess, video games)

**Cons:**
- No uncertainty measurement (RD)
- Assumes normal distribution
- No time decay (stale ratings)
- Poor for small sample sizes

### Implementation

See `indie_match_history/ratings.py:EloEngine`

### References

- Elo, A. (1978). *The Rating of Chess Players, Past and Present*. Arco.
- Tier 2: Industry standard

---

## Glicko-2 System

### Description

Mark Glickman's improvement over Glicko-1. Adds volatility parameter and iterative rating updates.

### Formula

Glicko-2 uses:

1. **Rating (µ)** - converted to 1500-scale
2. **Rating Deviation (φ)** - uncertainty in rating
3. **Volatility (σ)** - expected fluctuation in rating

#### Rating Update Process

1. Convert to internal scale (µ = (R - 1500) / 173.7178)
2. Compute expected outcome:
   ```
   E(µ, µ_j, φ_j) = 1 / (1 + exp(-g(φ_j)*(µ - µ_j)))
   ```
3. Update volatility via iterative algorithm (7-10 iterations)
4. Update rating and RD:
   ```
   φ* = sqrt(1 / (1/φ^2 + 1/v))
   µ' = µ + φ*^2 * Σ[g(φ_j)*(S_j - E_j)]
   ```
5. Convert back to 1500-scale

### Pros/Cons

**Pros:**
- Quantifies uncertainty (RD)
- Time decay (RD increases between matches)
- Volatility handles erratic players
- Better for new players (wide RD)

**Cons:**
- Computationally heavier (iterative)
- More parameters to tune
- Harder to explain to players

### Implementation

See `indie_match_history/ratings.py:Glicko2Engine`

- Uses 7 iteration loops for volatility (configurable)
- Auto-conversion between 1500-scale and internal scale
- Pure, deterministic (no external state)

### Parameters

Our defaults:

| Parameter | Value | Source |
|-----------|-------|--------|
| τ (tau) | 0.5 | Glickman (2012) |
| φ (initial RD) | 350 | Glickman (2012) |
| σ (initial volatility) | 0.06 | Glickman (2012) |

### References

- Glickman, M. (2012). *Example of the Glicko-2 System*. Boston University.
- Tier 1: Peer-reviewed methodology

---

## TrueSkill (Microsoft)

### Description

Bayesian ranking system for Xbox Live. Uses factor graphs, handles teams and draws.

### Key Differences

- Teams (not just 1v1)
- Draw probability modeled explicitly
- Factor graph inference (message passing)
- Skill = (µ, σ) distribution

### Why Not Implemented

1. **Complexity**: Requires factor graph library or custom implementation
2. **Patents**: Microsoft held patents (expired 2018-2022)
3. **Overkill**: Most indie games don't need team support
4. **Alternatives**: Glicko-2 sufficient for 1v1/FFA

### References

- Herbrich, R., Minka, T., & Graepel, T. (2007). *TrueSkill™: A Bayesian Skill Rating System*. Microsoft Research.
- Tier 1: Peer-reviewed

---

## Choosing a System

### Decision Matrix

| Situation | Recommendation |
|-----------|----------------|
| Simple 1v1 game, <1000 players | ELO (simpler) |
| New players, uncertain skill | Glicko-2 (RD tracks uncertainty) |
| Infrequent play | Glicko-2 (time decay) |
| Team-based games | TrueSkill (or custom) |
| Ranking leaderboards | Glicko-2 (sort by µ - k*φ for conservative rank) |
| Tournaments (many matches/day) | ELO (faster) |

### Engine Usage

```python
from indie_match_history import MatchHistoryEngine, EloEngine

# ELO
engine = MatchHistoryEngine(rating_system="elo")

# Glicko-2
engine = MatchHistoryEngine(rating_system="glicko2")

# Custom config
engine = MatchHistoryEngine(
    rating_system="glicko2",
    default_rating=1500.0,
)
```

---

## Hybrid Approaches

### ELO + Decay

Add time decay to ELO:

```python
# Inactive for >180 days: increase RD-like penalty
if days_since_last_match > 180:
    rating *= 0.99  # 1% decay per 180 days
```

### Conservative Ranking

For leaderboards, sort by `µ - 2*φ` (95% confidence lower bound):

```python
# Glicko-2 only
conservative_rating = rating.mu - 2 * rating.phi
```

This rewards active players with low uncertainty.

---

## Validation

### Testing Rating Systems

Our test suite validates:

1. **Determinism**: Same inputs → same outputs
2. **Monotonicity**: Winning increases rating
3. **Convergence**: Repeated updates converge
4. **Bounds**: Ratings stay within reasonable range

Run tests:

```bash
pytest tests/test_ratings.py -v
```

### References for Validation

- Kirsebom, O. (2023). *Validation of Rating Systems via Simulation*. ArXiv:2307.10832
- Tier 1: Preprint with methodology

---

## Open Questions

1. **Team support**: Should we implement TrueSkill or a simplified team extension?
2. **Matchmaking**: How to pair players for balanced matches?
3. **Seasonal resets**: Should ratings reset periodically?
4. **Smurf detection**: How to detect experienced players on new accounts?

---

## Engine Mapping

The rating systems map 1:1 to engine components:

| Analysis Concern | Engine Module |
|------------------|---------------|
| Rating algorithm choice | `ratings.py` (EloEngine, Glicko2Engine) |
| Rating storage | `models.py:Rating` |
| Rating updates | `engine.py:register_match()` |
| Rating queries | `storage/base.py:get_player_rating()` |

When analyzing rating system choices, always ground recommendations in the tested implementations in `ratings.py`.
