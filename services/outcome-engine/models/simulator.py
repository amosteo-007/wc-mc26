"""
Monte Carlo tournament simulator.

One rollout = one full tournament: group stage -> best thirds -> seeded knockout.
`run_simulation` plays N rollouts, applies a rejection-sampling condition per
rollout, and aggregates champion/finalist/path probabilities plus the number of
rollouts that satisfied the condition (`effective_runs`).
"""
import numpy as np
from typing import Dict, List, Optional
from collections import Counter

from models.strength import compute_goal_expectations, simulate_match_goals
from models.bracket import (
    rank_group, best_thirds, resolve_bracket, run_knockout, STAGE_ORDER,
)
from conditions.filters import build_condition_predicate

# Knockout milestones we report stage-reach probabilities for, weakest first.
# (Group is the start, champion is covered by champion_probs.)
_STAGE_ORDER = ['R32', 'R16', 'QF', 'SF', 'final']
_STAGE_RANK = {s: i for i, s in enumerate(STAGE_ORDER)}


def _STAGES_REACHED_FROM(furthest_stage: str) -> List[str]:
    """Reported stages that a team reaching `furthest_stage` also reached.

    A finalist (furthest='final') reached R32..final; the champion
    (furthest='champion') also reached the final and everything below it.
    """
    rank = _STAGE_RANK.get(furthest_stage, 0)
    return [s for s in _STAGE_ORDER if _STAGE_RANK[s] <= rank]


def simulate_one_tournament(
    groups: Dict[str, List[str]],
    bracket_spec: Dict,
    team_elos: Dict[str, float],
    rng: np.random.Generator,
) -> Dict:
    """Play a single full tournament and return its structured result.

    Result keys: champion, finalists, semifinalists, furthest (team -> stage),
    group_exits (set of teams that did not advance), penalty_final (bool).
    """
    group_standings_by_name: Dict[str, List[Dict]] = {}
    for group_name, teams in groups.items():
        results = {}
        for i in range(len(teams)):
            for j in range(i + 1, len(teams)):
                lh, la = compute_goal_expectations(
                    team_elos[teams[i]], team_elos[teams[j]]
                )
                hg, ag = simulate_match_goals(lh, la, rng)
                results[(teams[i], teams[j])] = (hg, ag)
        group_standings_by_name[group_name] = rank_group(teams, results)

    all_standings = list(group_standings_by_name.values())
    thirds = best_thirds(all_standings)

    advancing = set()
    for gs in all_standings:
        advancing.add(gs[0]['team'])
        advancing.add(gs[1]['team'])
    for bt in thirds:
        advancing.add(bt['team'])

    group_exits = {
        entry['team']
        for gs in all_standings
        for entry in gs
        if entry['team'] not in advancing
    }

    if bracket_spec.get('R32'):
        seeded = resolve_bracket(bracket_spec, group_standings_by_name, thirds)
    else:
        # No authored bracket: seed by the advancing set in a shuffled order.
        seeded = list(advancing)
        rng.shuffle(seeded)

    ko = run_knockout(seeded, team_elos, rng)
    ko['group_exits'] = group_exits
    return ko


def compute_form_adjustment(
    team_codes: List[str],
    team_elos: Dict[str, float],
    matches: List[Dict],
    reference_date=None,
) -> Dict[str, float]:
    """Compute per-team Elo adjustment based on recency-weighted results.

    For each match, compare the actual result to the Elo-expected result.
    Teams that outperform their rating get a positive adjustment;
    underperformers get a negative one.

    Adjustment is capped at ±40 Elo points so base rating still dominates.
    Without historical matches, returns zero adjustments for all teams.
    """
    from datetime import date

    if reference_date is None:
        reference_date = date.today()

    # Accumulators
    overperformance: Dict[str, float] = {c: 0.0 for c in team_codes}
    match_counts: Dict[str, int] = {c: 0 for c in team_codes}

    for m in matches:
        home = m['home_team']
        away = m['away_team']
        if home not in team_codes or away not in team_codes:
            continue

        elo_h = team_elos.get(home, 1800.0)
        elo_a = team_elos.get(away, 1800.0)

        # Expected result (Elo expectancy)
        expected_h = 1.0 / (1.0 + 10.0 ** ((elo_a - elo_h) / 400.0))

        # Actual result
        hg, ag = m['home_goals'], m['away_goals']
        if hg > ag:
            actual_h = 1.0
        elif ag > hg:
            actual_h = 0.0
        else:
            actual_h = 0.5

        # Recency weight
        match_date = m['match_date']
        if isinstance(match_date, str):
            match_date = date.fromisoformat(str(match_date)[:10])
        age_days = (reference_date - match_date).days
        age_days = max(age_days, 0)
        recency = 2.0 ** (-age_days / 730.0)  # 2-year half-life

        # Qualifier boost
        competition = m.get('competition', '')
        if 'qualif' in (competition or '').lower():
            recency *= 1.5

        # Overperformance: actual - expected, weighted by recency
        overperformance[home] += (actual_h - expected_h) * recency
        overperformance[away] += ((1.0 - actual_h) - (1.0 - expected_h)) * recency
        match_counts[home] += 1
        match_counts[away] += 1

    # Convert to Elo adjustment: scale by K-factor (~20 per match equivalent)
    # and cap at ±40
    adjustments = {}
    for code in team_codes:
        n = match_counts.get(code, 0)
        if n > 0:
            raw = (overperformance[code] / n) * 20.0 * min(n, 10)
            adjustments[code] = max(-40.0, min(40.0, raw))
        else:
            adjustments[code] = 0.0

    return adjustments


def run_simulation(
    teams: List[Dict],
    ratings: List[Dict],
    format_spec: Dict,
    n_runs: int = 10000,
    condition: Optional[Dict] = None,
    seed: Optional[int] = None,
    matches: Optional[List[Dict]] = None,
) -> Dict:
    """Run the full Monte Carlo with optional rejection sampling.

    Returns champion_probs, finalist_probs, top_paths, effective_runs, confidence.
    Probabilities are conditional on the condition (renormalized over the kept
    rollouts); `effective_runs` is how many of `n_runs` satisfied the condition.

    If `matches` is provided, recent historical results are used to compute a
    small per-team form adjustment (±40 Elo) on top of the base rating.
    """
    rng = np.random.default_rng(seed)

    team_elos: Dict[str, float] = {}
    for t in teams:
        team_ratings = [r['rating'] for r in ratings if r['team_id'] == t['id']]
        team_elos[t['fifa_code']] = (
            float(np.mean(team_ratings)) if team_ratings else 1800.0
        )

    # Apply form adjustments from historical matches
    form_adjustments: Dict[str, float] = {}
    if matches:
        codes = [t['fifa_code'] for t in teams]
        form_adjustments = compute_form_adjustment(codes, team_elos, matches)
        for code, adj in form_adjustments.items():
            team_elos[code] = team_elos.get(code, 1800.0) + adj

    groups = {g['group']: g['teams'] for g in format_spec.get('groups', [])}
    if not groups:
        all_teams = list(team_elos.keys())
        rng.shuffle(all_teams)
        groups = {chr(65 + i): all_teams[i * 4:(i + 1) * 4] for i in range(12)}

    bracket_spec = format_spec.get('knockout_bracket', {})
    predicate = build_condition_predicate(condition, team_elos)

    champion_counts = Counter()
    finalist_counts = Counter()
    path_counts = Counter()
    # For each knockout stage, count teams that reached *at least* that stage.
    stage_reach_counts = {s: Counter() for s in _STAGE_ORDER}
    effective_runs = 0

    for _ in range(n_runs):
        rollout = simulate_one_tournament(groups, bracket_spec, team_elos, rng)
        if not predicate(rollout):
            continue
        effective_runs += 1
        champion_counts[rollout['champion']] += 1
        for f in rollout['finalists']:
            finalist_counts[f] += 1
        if rollout['finalists']:
            pair = tuple(sorted(rollout['finalists']))
            path_counts[f"{pair[0]} vs {pair[1]}"] += 1
        # Credit each team for every stage it reached or surpassed.
        for code, stage in rollout['furthest'].items():
            for s in _STAGES_REACHED_FROM(stage):
                stage_reach_counts[s][code] += 1

    denom = effective_runs if effective_runs > 0 else 1
    champion_probs = {t: c / denom for t, c in champion_counts.items()}
    # A `team_wins` condition pins that team to champion in 100% of kept
    # rollouts — a tautology that carries no information. Drop it so the
    # redistribution board shows only the informative runner-up field.
    if condition and condition.get('type') == 'team_wins':
        pinned = (condition.get('params') or {}).get('team_fifa_code')
        champion_probs.pop(pinned, None)
    finalist_probs = {t: c / denom for t, c in finalist_counts.items()}
    top_paths = [
        {'final': matchup, 'probability': c / denom}
        for matchup, c in path_counts.most_common(10)
    ]
    # stage_probs[stage][team] = P(team reaches at least `stage` | condition)
    stage_probs = {
        s: {t: c / denom for t, c in counts.items()}
        for s, counts in stage_reach_counts.items()
    }

    confidence = {
        'data_quality': 'medium',
        'effective_runs': effective_runs,
        'requested_runs': n_runs,
        'acceptance_rate': effective_runs / n_runs if n_runs else 0.0,
        'thin_sample': effective_runs < 100,
        'rating_coverage': min(len(team_elos) / 48, 1.0),
    }

    return {
        'champion_probs': champion_probs,
        'finalist_probs': finalist_probs,
        'stage_probs': stage_probs,
        'top_paths': top_paths,
        'effective_runs': effective_runs,
        'confidence': confidence,
        'n_runs': n_runs,
    }
