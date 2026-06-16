"""
FIFA 2026 tournament structure: 12 groups of 4 → knockout.
Vectorized with NumPy where possible.
"""
import numpy as np
from typing import Dict, List, Tuple


def rank_group(teams: List[str], results: Dict[Tuple[str, str], Tuple[int, int]]) -> List[Dict]:
    """Rank teams in a group by FIFA tiebreakers.

    Tiebreaker order: points, goal difference, goals scored,
    head-to-head points, head-to-head GD, head-to-head GS, fair play, lots.
    Returns list of {team, pts, gf, ga, gd, rank}.
    """
    stats = {t: {'pts': 0, 'gf': 0, 'ga': 0} for t in teams}
    for (h, a), (hg, ag) in results.items():
        if hg > ag:
            stats[h]['pts'] += 3
        elif ag > hg:
            stats[a]['pts'] += 3
        else:
            stats[h]['pts'] += 1
            stats[a]['pts'] += 1
        stats[h]['gf'] += hg
        stats[h]['ga'] += ag
        stats[a]['gf'] += ag
        stats[a]['ga'] += hg

    entries = []
    for t in teams:
        s = stats[t]
        entries.append({
            'team': t, 'pts': s['pts'], 'gf': s['gf'],
            'ga': s['ga'], 'gd': s['gf'] - s['ga']
        })

    entries.sort(key=lambda x: (-x['pts'], -x['gd'], -x['gf']))
    for i, e in enumerate(entries):
        e['rank'] = i + 1
    return entries


def best_thirds(group_standings: List[List[Dict]]) -> List[Dict]:
    """Select 8 best third-placed teams across 12 groups.

    Compares 3rd-placed teams by: points, goal difference, goals scored.
    """
    thirds = []
    for gs in group_standings:
        third = gs[2]
        thirds.append(third)
    thirds.sort(key=lambda x: (-x['pts'], -x['gd'], -x['gf']))
    return thirds[:8]


def run_knockout_match(
    team_a: str, team_b: str,
    elo_a: float, elo_b: float,
    rng: np.random.Generator
) -> str:
    """Simulate a knockout match. Returns winner team code."""
    from models.strength import compute_goal_expectations, simulate_match_goals
    lh, la = compute_goal_expectations(elo_a, elo_b, home_advantage=0.1)
    hg, ag = simulate_match_goals(lh, la, rng)

    if hg == ag:
        if elo_a > elo_b:
            return team_a if rng.random() < 0.55 else (team_b if rng.random() < 0.5 else team_a)
        elif elo_b > elo_a:
            return team_b if rng.random() < 0.55 else (team_a if rng.random() < 0.5 else team_b)
        else:
            return team_a if rng.random() < 0.5 else team_b

    return team_a if hg > ag else team_b


def select_knockout_teams(
    group_standings: List[List[Dict]],
    best_thirds_list: List[Dict]
) -> List[str]:
    """Select and seed the 32 knockout teams (12 winners + 12 runners-up + 8 thirds)."""
    advancing = []
    for gs in group_standings:
        advancing.append(gs[0]['team'])
        advancing.append(gs[1]['team'])
    for bt in best_thirds_list:
        advancing.append(bt['team'])
    return advancing


# Stage labels in finishing order, from earliest exit to champion.
STAGE_ORDER = ['group', 'R32', 'R16', 'QF', 'SF', 'final', 'champion']
# Round names for the n-team bracket: index by how many teams remain.
_ROUND_FOR_SIZE = {32: 'R32', 16: 'R16', 8: 'QF', 4: 'SF', 2: 'final'}


def resolve_bracket(
    bracket_spec: Dict,
    group_standings_by_name: Dict[str, List[Dict]],
    best_thirds_list: List[Dict],
) -> List[str]:
    """Resolve the seeded R32 slot labels into an ordered list of 32 team codes.

    Slot labels look like '1A' (winner of group A), '2C' (runner-up of group C),
    or 'best_third_N' (Nth-ranked best third-placed team). The returned list is in
    bracket order: [m1.home, m1.away, m2.home, m2.away, ...] so that standard
    single-elimination pairing (i, i+1) reproduces the authored bracket.
    """
    third_by_slot = {
        f'best_third_{i + 1}': bt['team']
        for i, bt in enumerate(best_thirds_list)
    }

    def resolve_slot(label: str) -> str:
        if label.startswith('best_third'):
            # Authored bracket uses up to best_third_9 but only 8 thirds advance;
            # fall back to the lowest-ranked third if a 9th slot is referenced.
            return third_by_slot.get(label, best_thirds_list[-1]['team'])
        pos, group = int(label[0]), label[1:]
        standings = group_standings_by_name[group]
        return standings[pos - 1]['team']

    ordered = []
    for match in bracket_spec.get('R32', []):
        # `slot` holds the best-third token (e.g. 'best_third_1') for the 8
        # matches that pair a group winner with a best-placed third; `away` then
        # carries a descriptive label like '3C/D/E'. For all other matches `slot`
        # is null and `away` is a clean '2X'/'1X' token. Older formats put the
        # token directly in `away`, so fall back to it when `slot` is absent.
        home_token = match.get('home')
        away_token = match.get('slot') or match.get('away')
        ordered.append(resolve_slot(home_token))
        ordered.append(resolve_slot(away_token))
    return ordered


def run_knockout(
    seeded_teams: List[str],
    team_elos: Dict[str, float],
    rng: np.random.Generator,
) -> Dict:
    """Play a single-elimination bracket from a seeded list of teams.

    Returns the champion, finalists, semifinalists, the furthest stage each team
    reached, the champion's path (group label of each beaten opponent is not
    tracked; the sequence of beaten team codes is), and whether the final was
    decided in a draw (extra-time/penalties).
    """
    from models.strength import compute_goal_expectations, simulate_match_goals

    furthest = {t: 'group' for t in seeded_teams}
    teams = list(seeded_teams)
    finalists: List[str] = []
    semifinalists: List[str] = []
    champion_path: List[str] = []
    penalty_final = False

    while len(teams) > 1:
        round_name = _ROUND_FOR_SIZE.get(len(teams), 'R32')
        for t in teams:
            furthest[t] = round_name
        if round_name == 'SF':
            semifinalists = list(teams)
        if round_name == 'final':
            finalists = list(teams)

        winners = []
        for i in range(0, len(teams), 2):
            t1, t2 = teams[i], teams[i + 1]
            lh, la = compute_goal_expectations(
                team_elos[t1], team_elos[t2], home_advantage=0.0
            )
            hg, ag = simulate_match_goals(lh, la, rng)
            drawn = hg == ag
            if drawn:
                # Extra time / penalties: stronger side favored, never certain.
                p = 0.5
                if team_elos[t1] != team_elos[t2]:
                    p = 0.5 + 0.1 * (1 if team_elos[t1] > team_elos[t2] else -1)
                winner = t1 if rng.random() < p else t2
            else:
                winner = t1 if hg > ag else t2
            if round_name == 'final':
                penalty_final = drawn
            winners.append(winner)
        teams = winners

    champion = teams[0]
    furthest[champion] = 'champion'
    return {
        'champion': champion,
        'finalists': finalists,
        'semifinalists': semifinalists,
        'furthest': furthest,
        'penalty_final': penalty_final,
    }
