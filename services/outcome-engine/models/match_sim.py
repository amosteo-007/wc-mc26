"""Single-match Monte Carlo simulation.

Reuses the existing Poisson goal model from models/strength.py.
Provides a full breakdown: win/draw/loss, goal distributions,
over/under lines, both-teams-to-score, and top scorelines.
"""
import numpy as np
from typing import Dict, List, Optional
from collections import Counter

from models.strength import compute_goal_expectations, simulate_match_goals
from models.simulator import compute_form_adjustment


def simulate_match(
    home_elo: float,
    away_elo: float,
    n_runs: int = 20000,
    neutral: bool = True,
    is_host_home: bool = False,
    goal_line: Optional[float] = None,
    seed: Optional[int] = None,
    form_applied: bool = False,
    rating_coverage: float = 1.0,
) -> Dict:
    """Run single-match Monte Carlo and return a full breakdown.

    Args:
        home_elo: Effective Elo rating for home team (after form adjustment).
        away_elo: Effective Elo rating for away team.
        n_runs: Number of Monte Carlo runs.
        neutral: If True, no home advantage.
        is_host_home: If True, home team gets host boost (only when not neutral).
        goal_line: If set, compute P(total_goals >= goal_line).
        seed: Optional RNG seed.
        form_applied: Whether recent-form adjustment was baked into the elos.
        rating_coverage: Fraction of teams with real ratings (1.0 = both covered).

    Returns dict with keys:
        win_home, draw, win_away -- probabilities (0-1).
        expected_goals_home, expected_goals_away, expected_total -- expectations.
        total_goals_distribution -- {0,1,2,3,4,'5+'} -> prob.
        over_under -- dict of over/under probs for lines 0.5-4.5.
        both_teams_score -- probability both teams score >=1.
        top_scorelines -- most-frequent "H-A" scorelines with prob.
        goal_line_query -- if goal_line provided, P(total >= goal_line).
        confidence -- n_runs, rating_coverage, form_applied.
    """
    rng = np.random.default_rng(seed)

    home_advantage = 0.0 if neutral else 0.35
    host_boost = is_host_home and not neutral

    lh, la = compute_goal_expectations(
        home_elo, away_elo, home_advantage=home_advantage, is_host=host_boost
    )

    home_wins = 0
    draws = 0
    away_wins = 0
    home_goals_sum = 0
    away_goals_sum = 0
    both_scored = 0
    total_goals_list = []
    scorelines = Counter()

    for _ in range(n_runs):
        hg, ag = simulate_match_goals(lh, la, rng)
        home_goals_sum += hg
        away_goals_sum += ag
        total_goals_list.append(hg + ag)

        if hg > ag:
            home_wins += 1
        elif ag > hg:
            away_wins += 1
        else:
            draws += 1

        if hg >= 1 and ag >= 1:
            both_scored += 1

        scorelines[f"{hg}-{ag}"] += 1

    denom = n_runs if n_runs > 0 else 1

    # Total goals distribution (0, 1, 2, 3, 4, 5+). The explicit buckets stop at
    # 4 so the "5+" tail captures everything >=5 exactly once — overlapping the
    # two would make the distribution sum to >1.
    dist_counter = Counter(total_goals_list)
    total_goals_dist = {}
    for g in range(5):
        total_goals_dist[str(g)] = dist_counter.get(g, 0) / denom
    five_plus = sum(c for g, c in dist_counter.items() if g >= 5)
    total_goals_dist["5+"] = five_plus / denom

    # Over/under lines
    over_under = {}
    for line in [0.5, 1.5, 2.5, 3.5, 4.5]:
        over_count = sum(1 for g in total_goals_list if g >= line)
        key = f"over_{str(line).replace('.', '_')}"
        under_key = f"under_{str(line).replace('.', '_')}"
        over_under[key] = over_count / denom
        over_under[under_key] = 1.0 - over_under[key]

    # Goal line query
    goal_line_result = None
    if goal_line is not None:
        over_gl = sum(1 for g in total_goals_list if g >= goal_line)
        goal_line_result = {
            'line': goal_line,
            'prob_over': over_gl / denom,
            'prob_under': 1.0 - (over_gl / denom),
        }

    # Top scorelines
    top_scorelines = [
        {'scoreline': sl, 'probability': c / denom}
        for sl, c in scorelines.most_common(10)
    ]

    return {
        'win_home': home_wins / denom,
        'draw': draws / denom,
        'win_away': away_wins / denom,
        'expected_goals_home': round(float(lh), 2),
        'expected_goals_away': round(float(la), 2),
        'expected_total': round(float(lh + la), 2),
        'mean_simulated_home': round(home_goals_sum / denom, 2),
        'mean_simulated_away': round(away_goals_sum / denom, 2),
        'total_goals_distribution': total_goals_dist,
        'over_under': over_under,
        'both_teams_score': both_scored / denom,
        'top_scorelines': top_scorelines,
        'goal_line_query': goal_line_result,
        'confidence': {
            'n_runs': n_runs,
            'rating_coverage': rating_coverage,
            'form_applied': form_applied,
        },
    }
