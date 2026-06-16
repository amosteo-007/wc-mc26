"""
Elo-to-expectancy conversion and Poisson goal model.

P(A beats B) = 1 / (1 + 10^((elo_B - elo_A) / 400))
Home advantage: ~0.3 goals (neutral), ~0.5 (host)
"""
import numpy as np
from typing import Tuple

HOME_ADVANTAGE = 0.35  # goals
HOST_BOOST = 0.15  # additional for host nation


def elo_to_expectancy(elo_a: float, elo_b: float) -> float:
    """Probability team A beats team B (regulation time)."""
    return 1.0 / (1.0 + 10.0 ** ((elo_b - elo_a) / 400.0))


def elo_to_draw_prob(elo_diff: float) -> float:
    """Estimate draw probability from Elo difference. Max ~0.28 at elo_diff=0."""
    return 0.28 * np.exp(-0.001 * elo_diff ** 2)


def compute_goal_expectations(
    elo_home: float, elo_away: float,
    home_advantage: float = HOME_ADVANTAGE,
    is_host: bool = False
) -> Tuple[float, float]:
    """Compute expected goals (lambda) for home and away teams.

    Returns (lambda_home, lambda_away) for bivariate Poisson model.
    Base rate ~1.35 goals per team, adjusted by Elo difference / 400.
    """
    boost = home_advantage + (HOST_BOOST if is_host else 0)
    elo_diff = elo_home - elo_away

    base_rate = 1.35
    lambda_home = base_rate + elo_diff / 400.0 + boost
    lambda_away = base_rate - elo_diff / 400.0 - boost * 0.3

    return max(lambda_home, 0.3), max(lambda_away, 0.2)


def simulate_match_goals(
    lambda_home: float, lambda_away: float, rng: np.random.Generator
) -> Tuple[int, int]:
    """Simulate a single match's goals using independent Poisson draws."""
    home_goals = rng.poisson(lambda_home)
    away_goals = rng.poisson(lambda_away)
    return home_goals, away_goals


def simulate_match_outcome(
    elo_home: float, elo_away: float,
    rng: np.random.Generator,
    home_advantage: float = HOME_ADVANTAGE,
    is_host: bool = False,
    knockout: bool = False
) -> Tuple[int, int, str]:
    """Simulate a match. Returns (home_goals, away_goals, winner).

    For knockout matches with draws, simulate extra time (60% stronger wins)
    then penalties (50/50).
    """
    lh, la = compute_goal_expectations(elo_home, elo_away, home_advantage, is_host)
    hg, ag = simulate_match_goals(lh, la, rng)

    if knockout and hg == ag:
        if elo_home > elo_away:
            hg += 1 if rng.random() < 0.6 else (1 if rng.random() < 0.5 else 0)
        elif elo_away > elo_home:
            ag += 1 if rng.random() < 0.6 else (1 if rng.random() < 0.5 else 0)
        else:
            if rng.random() < 0.5:
                hg += 1
            else:
                ag += 1

    if hg > ag:
        winner = 'home'
    elif ag > hg:
        winner = 'away'
    else:
        winner = 'draw'
    return hg, ag, winner
