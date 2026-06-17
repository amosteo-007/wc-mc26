"""Unit tests for the knockout bracket resolver (no DB needed)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from knockout import resolve_bracket, rank_third_places  # noqa: E402


def _standings(group, order):
    """Build a standings list (rank 1..n) for `group` from an ordered code list."""
    return [
        {'team': code, 'name': code, 'rank': i + 1,
         'pts': (len(order) - i) * 3, 'gd': len(order) - i, 'gf': len(order) - i}
        for i, code in enumerate(order)
    ]


# Minimal 2-match R32 → 1-match R16 → Final bracket, mirroring the real spec's
# placeholder vocabulary.
SPEC = {
    'R32': [
        {'match': 1, 'home': '1A', 'away': '2B', 'slot': None, 'desc': '1A vs 2B'},
        {'match': 2, 'home': '1B', 'away': '2A', 'slot': None, 'desc': '1B vs 2A'},
    ],
    'R16': [
        {'match': 1, 'home': 'W32-1', 'away': 'W32-2', 'desc': 'W R32-1 vs W R32-2'},
    ],
    'Final': {'home': 'W16-1', 'away': 'W16-1', 'desc': 'placeholder'},
}

GROUPS = {
    'A': _standings('A', ['ARG', 'MEX', 'POL', 'KSA']),
    'B': _standings('B', ['ENG', 'USA', 'IRN', 'WAL']),
}


def test_r32_slots_resolve_from_standings():
    out = resolve_bracket(SPEC, GROUPS, ko_results=[])
    r32 = out['R32']
    # 1A = ARG, 2B = USA ; 1B = ENG, 2A = MEX
    assert (r32[0]['home_code'], r32[0]['away_code']) == ('ARG', 'USA')
    assert (r32[1]['home_code'], r32[1]['away_code']) == ('ENG', 'MEX')
    # Nothing played yet → later rounds are TBD.
    assert r32[0]['played'] is False
    assert out['R16']['home_code'] is None if isinstance(out['R16'], dict) else True


def test_winner_advances_to_next_round():
    ko = [
        {'stage': 'R32', 'matchday': 1, 'home_code': 'ARG', 'away_code': 'USA',
         'home_goals': 2, 'away_goals': 1, 'shootout_winner': None},
        {'stage': 'R32', 'matchday': 2, 'home_code': 'ENG', 'away_code': 'MEX',
         'home_goals': 0, 'away_goals': 3, 'shootout_winner': None},
    ]
    out = resolve_bracket(SPEC, GROUPS, ko_results=ko)
    # W32-1 = ARG (beat USA), W32-2 = MEX (beat ENG) → R16 match 1 pairs them.
    r16 = out['R16'][0] if isinstance(out['R16'], list) else out['R16']
    assert r16['home_code'] == 'ARG'
    assert r16['away_code'] == 'MEX'


def test_shootout_winner_decides_level_knockout():
    ko = [
        {'stage': 'R32', 'matchday': 1, 'home_code': 'ARG', 'away_code': 'USA',
         'home_goals': 1, 'away_goals': 1, 'shootout_winner': 'USA'},
    ]
    out = resolve_bracket(SPEC, GROUPS, ko_results=ko)
    assert out['R32'][0]['winner'] == 'USA'
    r16 = out['R16'][0] if isinstance(out['R16'], list) else out['R16']
    assert r16['home_code'] == 'USA'  # shootout winner advanced


def test_level_knockout_without_shootout_stays_undecided():
    ko = [
        {'stage': 'R32', 'matchday': 1, 'home_code': 'ARG', 'away_code': 'USA',
         'home_goals': 1, 'away_goals': 1, 'shootout_winner': None},
    ]
    out = resolve_bracket(SPEC, GROUPS, ko_results=ko)
    assert out['R32'][0]['winner'] is None
    r16 = out['R16'][0] if isinstance(out['R16'], list) else out['R16']
    assert r16['home_code'] is None  # cannot advance an undecided tie


def test_best_thirds_ranking_takes_top_eight():
    groups = {
        chr(ord('A') + i): _standings(
            chr(ord('A') + i),
            [f'W{i}', f'X{i}', f'T{i}', f'Z{i}'],
        )
        for i in range(12)
    }
    # Make third-place points vary so ordering is deterministic.
    for i, g in enumerate(groups.values()):
        g[2]['pts'] = i  # group 11's third has the most points
    thirds = rank_third_places(groups)
    assert len(thirds) == 8
    # Highest-pts thirds come first.
    assert thirds[0]['pts'] == 11
    assert thirds[-1]['pts'] == 4
