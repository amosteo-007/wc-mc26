"""Resolve the knockout bracket forward from real results.

The authored ``knockout_bracket`` in ``tournament_format.spec`` uses symbolic
placeholders rather than team codes:

- R32 slots: ``"1A"`` (winner group A), ``"2C"`` (runner-up C), or a best-third
  token carried in the ``slot`` key (``"best_third_1"``) with ``away`` holding a
  human label like ``"3C/D/E"``.
- Later rounds: ``"W32-1"`` (winner of R32 match 1), ``"WQF-1"`` (winner QF 1),
  ``"LSF-1"`` (loser SF 1, for the 3rd-place match), ``"WSF-1"`` (winner SF 1).

This module turns those placeholders into real FIFA codes using the live group
standings plus whatever knockout match results have landed so far. A placeholder
whose feeder match hasn't been played yet stays unresolved (``None``) so the UI
can render it as TBD — the bracket "auto-advances" as results arrive.

It is deliberately self-contained (pure functions over plain dicts) so it can be
unit-tested without a DB and reused by ``database.get_tournament_state``.
"""
from typing import Dict, List, Optional, Tuple

# Round progression, earliest to latest. Each round's winners/losers feed the
# next, so resolving in this order means a round only depends on earlier ones.
_ROUND_ORDER = ['R32', 'R16', 'QF', 'SF', '3rd_place', 'Final']

# Placeholder prefixes → the stage whose result they reference.
# 'W32-3' → winner of stage R32, match 3; 'LSF-1' → loser of SF match 1.
_WINNER_PREFIX_STAGE = {'W32': 'R32', 'W16': 'R16', 'WQF': 'QF', 'WSF': 'SF'}
_LOSER_PREFIX_STAGE = {'LSF': 'SF'}


def rank_third_places(group_standings_by_name: Dict[str, List[Dict]]) -> List[Dict]:
    """Rank the 12 third-placed teams; return the 8 that advance (FIFA order).

    Each standings list is assumed already sorted (rank 1..4). A third-placed
    entry must have ``rank == 3``; groups that haven't produced a full table yet
    are skipped (so best-thirds only firm up once the group stage completes).
    """
    thirds = []
    for gname, standings in group_standings_by_name.items():
        third = next((s for s in standings if s.get('rank') == 3), None)
        if third is not None:
            thirds.append({**third, 'group': gname})
    thirds.sort(key=lambda s: (-s.get('pts', 0), -s.get('gd', 0), -s.get('gf', 0), s.get('team', '')))
    return thirds[:8]


def _index_knockout_results(ko_results: List[Dict]) -> Dict[Tuple[str, int], Dict]:
    """Index knockout result rows by (stage, match_number).

    Rows come from ``wc_results`` with ``stage`` in R32/R16/QF/SF/3rd_place/Final.
    The match number is taken from ``matchday`` (the upsert stores the bracket
    match index there for knockout rows).
    """
    by_key: Dict[Tuple[str, int], Dict] = {}
    for r in ko_results:
        stage = r.get('stage')
        match_no = r.get('matchday')
        if stage and match_no is not None:
            by_key[(stage, int(match_no))] = r
    return by_key


def _winner_loser(row: Dict) -> Tuple[Optional[str], Optional[str]]:
    """Return (winner_code, loser_code) for a played knockout row.

    Knockout games can't truly draw; if the recorded score is level we assume a
    shootout winner was stored via an optional ``shootout_winner`` field, else we
    can't decide a winner yet (returns None,None so it stays TBD)."""
    h, a = row.get('home_code'), row.get('away_code')
    hg, ag = row.get('home_goals'), row.get('away_goals')
    if h is None or a is None or hg is None or ag is None:
        return None, None
    if hg > ag:
        return h, a
    if ag > hg:
        return a, h
    so = row.get('shootout_winner')
    if so == h:
        return h, a
    if so == a:
        return a, h
    return None, None  # level with no shootout winner recorded → undecided


def resolve_bracket(
    bracket_spec: Dict,
    group_standings_by_name: Dict[str, List[Dict]],
    ko_results: List[Dict],
) -> Dict:
    """Resolve every bracket slot to a team code where the feeder result exists.

    Returns a dict mirroring the bracket spec's structure, where each match is
    ``{match, home, away, home_code, away_code, played, home_goals, away_goals,
    winner, desc}``. ``home_code``/``away_code`` are real FIFA codes or None
    (TBD). This is what the tournament view renders.
    """
    best_thirds = rank_third_places(group_standings_by_name)
    third_by_slot = {f'best_third_{i + 1}': bt['team'] for i, bt in enumerate(best_thirds)}
    results = _index_knockout_results(ko_results)

    # Winners/losers per resolved stage, filled as we walk rounds in order.
    stage_winners: Dict[str, Dict[int, str]] = {}
    stage_losers: Dict[str, Dict[int, str]] = {}

    def resolve_token(token: Optional[str]) -> Optional[str]:
        """Map a single placeholder token to a team code, or None if not yet known."""
        if not token:
            return None
        if token.startswith('best_third_'):
            return third_by_slot.get(token)
        # Group winner/runner-up: '1A', '2C'. First char is position, rest is group.
        if len(token) >= 2 and token[0] in '123' and token[1:].isalpha():
            pos, group = int(token[0]), token[1:]
            standings = group_standings_by_name.get(group)
            if standings and len(standings) >= pos:
                return standings[pos - 1].get('team')
            return None
        # Winner/loser of an earlier knockout match: 'W32-3', 'WQF-1', 'LSF-2'.
        if '-' in token:
            prefix, num = token.split('-', 1)
            if not num.isdigit():
                return None
            n = int(num)
            if prefix in _WINNER_PREFIX_STAGE:
                stage = _WINNER_PREFIX_STAGE[prefix]
                return stage_winners.get(stage, {}).get(n)
            if prefix in _LOSER_PREFIX_STAGE:
                stage = _LOSER_PREFIX_STAGE[prefix]
                return stage_losers.get(stage, {}).get(n)
        return None

    def build_match(stage: str, m: Dict) -> Dict:
        match_no = m.get('match')
        home_code = resolve_token(m.get('home'))
        # R32 best-third matches carry the token in `slot`; otherwise in `away`.
        away_code = resolve_token(m.get('slot') or m.get('away'))
        out = {
            'match': match_no,
            'home': m.get('home'),
            'away': m.get('away'),
            'home_code': home_code,
            'away_code': away_code,
            'desc': m.get('desc'),
            'played': False,
            'home_goals': None,
            'away_goals': None,
            'winner': None,
        }
        row = results.get((stage, match_no)) if match_no is not None else None
        if row is not None:
            w, l = _winner_loser(row)
            out.update({
                'played': w is not None,
                'home_goals': row.get('home_goals'),
                'away_goals': row.get('away_goals'),
                'winner': w,
                # Prefer the actual recorded teams over the resolved placeholders
                # (they should match, but the result row is ground truth).
                'home_code': row.get('home_code') or home_code,
                'away_code': row.get('away_code') or away_code,
            })
            if match_no is not None and w is not None:
                stage_winners.setdefault(stage, {})[match_no] = w
                stage_losers.setdefault(stage, {})[match_no] = l
        return out

    resolved: Dict[str, object] = {}
    for stage in _ROUND_ORDER:
        spec = bracket_spec.get(stage)
        if spec is None:
            continue
        if isinstance(spec, list):
            resolved[stage] = [build_match(stage, m) for m in spec]
        else:
            # Single-match rounds (3rd_place, Final) have no `match` index in the
            # spec — give them match 1 so result lookup works.
            single = {**spec, 'match': spec.get('match', 1)}
            resolved[stage] = build_match(stage, single)

    resolved['best_thirds'] = [
        {'team': bt['team'], 'group': bt.get('group'), 'pts': bt.get('pts'),
         'gd': bt.get('gd'), 'gf': bt.get('gf')}
        for bt in best_thirds
    ]
    # The champion is the Final winner, once played.
    final = resolved.get('Final')
    resolved['champion'] = final.get('winner') if isinstance(final, dict) else None
    return resolved
