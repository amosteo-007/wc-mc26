"""Unit tests for single-match Monte Carlo simulation."""
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from models.match_sim import simulate_match


def test_higher_elo_wins_more_often():
    """Strong team (2100) should beat weak team (1700) more than lose."""
    result = simulate_match(home_elo=2100, away_elo=1700, n_runs=5000, seed=42)
    assert result['win_home'] > result['win_away']
    assert result['win_home'] > 0.5  # strong favorite at home


def test_probabilities_sum_to_one():
    """Win + draw + loss should equal 1."""
    result = simulate_match(home_elo=1900, away_elo=1900, n_runs=5000, seed=1)
    total = result['win_home'] + result['draw'] + result['win_away']
    assert abs(total - 1.0) < 1e-9


def test_total_goals_distribution_sums_to_one():
    """Total goals distribution should sum to ~1."""
    result = simulate_match(home_elo=2000, away_elo=1800, n_runs=5000, seed=3)
    total = sum(result['total_goals_distribution'].values())
    assert abs(total - 1.0) < 1e-9


def test_goal_line_query():
    """goal_line=3 should return P(>=3) in (0, 1)."""
    result = simulate_match(home_elo=2000, away_elo=1800, n_runs=5000, goal_line=3, seed=7)
    assert result['goal_line_query'] is not None
    prob = result['goal_line_query']['prob_over']
    assert 0.0 < prob < 1.0
    assert abs(result['goal_line_query']['prob_over'] + result['goal_line_query']['prob_under'] - 1.0) < 1e-9


def test_neutral_venue_equalizes():
    """Neutral venue should give more balanced result than home advantage."""
    home_result = simulate_match(home_elo=1900, away_elo=1900, n_runs=5000, neutral=False, seed=5)
    neutral_result = simulate_match(home_elo=1900, away_elo=1900, n_runs=5000, neutral=True, seed=5)
    # Home advantage should push win_home up
    assert home_result['win_home'] > neutral_result['win_home']


def test_both_teams_score_in_range():
    """BTS probability should be in (0, 1)."""
    result = simulate_match(home_elo=2000, away_elo=1800, n_runs=5000, seed=9)
    assert 0.0 < result['both_teams_score'] < 1.0


def test_top_scorelines_sorted():
    """Top scorelines should be sorted by probability descending."""
    result = simulate_match(home_elo=2000, away_elo=1800, n_runs=5000, seed=11)
    probs = [s['probability'] for s in result['top_scorelines']]
    assert probs == sorted(probs, reverse=True)


def test_over_under_lines():
    """All over/under lines should have valid probabilities."""
    result = simulate_match(home_elo=2000, away_elo=1800, n_runs=5000, seed=13)
    for key in ['over_0_5', 'over_1_5', 'over_2_5', 'over_3_5', 'over_4_5']:
        assert 0.0 <= result['over_under'].get(key, 0) <= 1.0


def test_reproducible_with_seed():
    """Same seed should produce identical results."""
    r1 = simulate_match(home_elo=2000, away_elo=1800, n_runs=5000, seed=42)
    r2 = simulate_match(home_elo=2000, away_elo=1800, n_runs=5000, seed=42)
    assert r1['win_home'] == r2['win_home']
    assert r1['draw'] == r2['draw']
    assert r1['win_away'] == r2['win_away']
