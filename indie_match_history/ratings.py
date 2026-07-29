"""Rating engines: ELO and Glicko-2.

Both engines are pure functions over rating state + a series of game outcomes.
They are deterministic, side-effect free, and backend-agnostic so they can be
unit-tested in isolation and reused by any storage backend.

References (see SECOND-KNOWLEDGE-BRAIN.md):
  - Glickman, M. (2012). "Example of the Glicko-2 system". J. Quant. Anal. Sports.
  - Elo, A. (1978). "The Rating of Chessplayers, Past and Present".
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, Protocol

from .errors import RatingError
from .models import MatchOutcome, Rating, RatingSystem


class RatingEngine(Protocol):
    """Protocol every rating engine implements."""

    system: RatingSystem

    def default_rating(self) -> Rating: ...

    def update(
        self, rating: Rating, opponents: Iterable[tuple[Rating, MatchOutcome]]
    ) -> Rating:
        """Return a new rating after a batch of games against opponents."""
        ...


# ---------------------------------------------------------------------------
# ELO
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EloEngine:
    """Standard Elo with logistic expected score and a K-factor ladder.

    Implements FIDE-style K-factor selection:
      - provisional (<30 games, modelled via rating < 2200): K=40
      - mid (rating < 2400): K=20
      - top (rating >= 2400): K=10
    The K ladder keeps new players volatile and stabilizes masters, matching
    common competitive-game practice.
    """

    system: RatingSystem = RatingSystem.ELO
    k_provisional: float = 40.0
    k_mid: float = 20.0
    k_top: float = 10.0
    top_threshold: float = 2400.0
    mid_threshold: float = 2200.0

    def default_rating(self) -> Rating:
        return Rating(value=1200.0, system=self.system)

    def _k_for(self, rating: Rating) -> float:
        v = rating.value
        if v < self.mid_threshold:
            return self.k_provisional
        if v < self.top_threshold:
            return self.k_mid
        return self.k_top

    @staticmethod
    def expected(player: float, opponent: float) -> float:
        """Standard logistic expected score for the player."""
        return 1.0 / (1.0 + math.pow(10.0, (opponent - player) / 400.0))

    def update(
        self, rating: Rating, opponents: Iterable[tuple[Rating, MatchOutcome]]
    ) -> Rating:
        opps = list(opponents)
        if not opps:
            raise RatingError("elo update requires at least one opponent")
        k = self._k_for(rating)
        delta = 0.0
        for opp_rating, outcome in opps:
            expected = self.expected(rating.value, opp_rating.value)
            actual = {
                MatchOutcome.WIN: 1.0,
                MatchOutcome.DRAW: 0.5,
                MatchOutcome.LOSS: 0.0,
                MatchOutcome.FORFEIT: 0.0,
            }[outcome]
            delta += k * (actual - expected)
        new_value = max(0.0, round(rating.value + delta, 2))
        return Rating(value=new_value, system=self.system)


# ---------------------------------------------------------------------------
# Glicko-2
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Glicko2Engine:
    """Glicko-2 rating system (Glickman 2012, step-by-step).

    Parameters mirror the reference example: tau constrains volatility changes,
    scale=173.7201 converts between internal (mu) and external (rating) scales.
    """

    system: RatingSystem = RatingSystem.GLICKO2
    default_value: float = 1500.0
    default_rd: float = 350.0
    default_vol: float = 0.06
    tau: float = 0.5
    scale: float = 173.7201
    epsilon: float = 1e-6

    def default_rating(self) -> Rating:
        return Rating(
            value=self.default_value,
            rd=self.default_rd,
            vol=self.default_vol,
            system=self.system,
        )

    def _g(self, phi: float) -> float:
        return 1.0 / math.sqrt(1.0 + 3.0 * phi * phi / (math.pi * math.pi))

    def update(
        self, rating: Rating, opponents: Iterable[tuple[Rating, MatchOutcome]]
    ) -> Rating:
        opps = list(opponents)
        if not opps:
            raise RatingError("glicko2 update requires at least one opponent")

        mu = (rating.value - self.default_value) / self.scale
        phi = rating.rd / self.scale
        sigma = rating.vol

        # Step 3: compute v
        # Step 4: compute Delta
        v_inv = 0.0
        delta_sum = 0.0
        for opp_rating, outcome in opps:
            mu_j = (opp_rating.value - self.default_value) / self.scale
            phi_j = opp_rating.rd / self.scale
            g_j = self._g(phi_j)
            e_j = 1.0 / (1.0 + math.exp(-g_j * (mu - mu_j)))
            s = {
                MatchOutcome.WIN: 1.0,
                MatchOutcome.DRAW: 0.5,
                MatchOutcome.LOSS: 0.0,
                MatchOutcome.FORFEIT: 0.0,
            }[outcome]
            v_inv += (g_j * g_j) * e_j * (1.0 - e_j)
            delta_sum += g_j * (s - e_j)
        v = 1.0 / v_inv
        delta = v * delta_sum

        # Step 5: determine new volatility via iteration
        a = math.log(sigma * sigma)
        phi_sq = phi * phi

        def f(x: float) -> float:
            ex = math.exp(x)
            num = ex * (delta * delta - phi_sq - v - ex)
            den = 2.0 * (phi_sq + v + ex) ** 2
            return num / den - (x - a) / (self.tau * self.tau)

        # Initial bounds
        a_val = a
        if delta * delta > phi_sq + v:
            b_val = math.log(delta * delta - phi_sq - v)
        else:
            k = 1.0
            while f(a_val - k * self.tau) < 0:
                k += 1
            b_val = a_val - k * self.tau

        fa = f(a_val)
        fb = f(b_val)
        while abs(b_val - a_val) > self.epsilon:
            c_val = a_val + (a_val - b_val) * fa / (fb - fa)
            fc = f(c_val)
            if fc * fb <= 0:
                a_val, fa = b_val, fb
            else:
                fa = fa / 2.0
            b_val, fb = c_val, fc
        new_sigma = math.exp(a_val / 2.0)

        # Step 6-8: update phi and mu
        phi_star = math.sqrt(phi_sq + new_sigma * new_sigma)
        new_phi = 1.0 / math.sqrt(1.0 / (phi_star * phi_star) + 1.0 / v)
        new_mu = mu + new_phi * new_phi * delta_sum

        new_value = self.default_value + self.scale * new_mu
        new_rd = new_phi * self.scale
        # Round and clamp rd to a sensible ceiling so it never exceeds default.
        new_rd = min(round(new_rd, 2), self.default_rd)
        new_value = max(0.0, round(new_value, 2))
        return Rating(
            value=new_value, rd=max(new_rd, 1.0), vol=round(new_sigma, 6),
            system=self.system,
        )


def make_engine(system: str | RatingSystem) -> RatingEngine:
    """Factory for a rating engine by name."""
    sys_ = RatingSystem.parse(system) if isinstance(system, str) else system
    if sys_ == RatingSystem.ELO:
        return EloEngine()
    if sys_ == RatingSystem.GLICKO2:
        return Glicko2Engine()
    raise RatingError(f"unknown rating system {system!r}")