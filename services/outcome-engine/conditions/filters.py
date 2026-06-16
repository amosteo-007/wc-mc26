"""Rejection sampling filters for Monte Carlo conditions."""
from typing import Callable, Dict, List, Optional

# Teams below this Elo are treated as "underdogs" for the underdog conditions.
UNDERDOG_ELO_CEILING = 1900.0
# Co-hosts of WC2026.
HOST_CODES = ('USA', 'MEX', 'CAN')

PRESET_CONDITIONS = {
    'team_exits_group': {
        'type': 'team_exits_group',
        'description': 'Selected team fails to advance from group stage',
        'params': {'team_fifa_code': 'string'}
    },
    'team_reaches_r16': {
        'type': 'team_reaches_r16',
        'description': 'Selected team reaches the Round of 16',
        'params': {'team_fifa_code': 'string'}
    },
    'team_reaches_qf': {
        'type': 'team_reaches_qf',
        'description': 'Selected team reaches quarter-finals',
        'params': {'team_fifa_code': 'string'}
    },
    'team_reaches_sf': {
        'type': 'team_reaches_sf',
        'description': 'Selected team reaches the semi-finals',
        'params': {'team_fifa_code': 'string'}
    },
    'team_reaches_final': {
        'type': 'team_reaches_final',
        'description': 'Selected team reaches the final',
        'params': {'team_fifa_code': 'string'}
    },
    'team_wins': {
        'type': 'team_wins',
        'description': 'Selected team wins the World Cup',
        'params': {'team_fifa_code': 'string'}
    },
    'host_underperforms': {
        'type': 'host_underperforms',
        'description': 'All host nations (USA, MEX, CAN) fail to advance',
        'params': {}
    },
    'underdog_semifinal': {
        'type': 'underdog_semifinal',
        'description': 'A team below Elo 1900 reaches semifinals',
        'params': {}
    },
    'penalty_final': {
        'type': 'penalty_final',
        'description': 'Final decided by penalty shootout',
        'params': {}
    },
    'refereeing_controversy': {
        'type': 'refereeing_controversy',
        'description': 'Major refereeing controversy impacts a knockout match',
        'params': {}
    }
}


def get_preset_conditions() -> list:
    """Return all available preset conditions."""
    return [{'id': k, **v} for k, v in PRESET_CONDITIONS.items()]


def get_condition_template(condition_id: str) -> Optional[Dict]:
    """Get a single condition template by ID."""
    return PRESET_CONDITIONS.get(condition_id)


# Stage ranking so "reaches QF" means "QF or better".
_STAGE_RANK = {
    'group': 0, 'R32': 1, 'R16': 2, 'QF': 3, 'SF': 4, 'final': 5, 'champion': 6,
}


def build_condition_predicate(
    condition: Optional[Dict],
    team_elos: Dict[str, float],
) -> Callable[[Dict], bool]:
    """Compile a condition dict into a predicate over a single tournament rollout.

    The rollout dict is what `run_knockout` returns merged with group-exit info:
      {champion, finalists, semifinalists, furthest: {team: stage},
       penalty_final, group_exits: set(team)}.

    Returns a callable rollout -> bool. An unknown or missing condition matches
    everything (no rejection), so unconditional runs keep every rollout.
    """
    if not condition:
        return lambda rollout: True

    ctype = condition.get('type')
    params = condition.get('params', {})
    team = params.get('team_fifa_code')

    def reached(rollout: Dict, code: str, stage: str) -> bool:
        return _STAGE_RANK.get(rollout['furthest'].get(code, 'group'), 0) >= _STAGE_RANK[stage]

    if ctype == 'team_wins':
        return lambda r: r['champion'] == team
    if ctype == 'team_exits_group':
        return lambda r: team in r['group_exits']
    if ctype == 'team_reaches_r16':
        return lambda r: reached(r, team, 'R16')
    if ctype == 'team_reaches_qf':
        return lambda r: reached(r, team, 'QF')
    if ctype == 'team_reaches_sf':
        return lambda r: reached(r, team, 'SF')
    if ctype == 'team_reaches_final':
        return lambda r: reached(r, team, 'final')
    if ctype == 'host_underperforms':
        return lambda r: all(h in r['group_exits'] for h in HOST_CODES)
    if ctype == 'penalty_final':
        return lambda r: r['penalty_final']
    if ctype == 'underdog_semifinal':
        underdogs = {c for c, e in team_elos.items() if e < UNDERDOG_ELO_CEILING}
        return lambda r: any(c in underdogs for c in r['semifinalists'])
    if ctype == 'refereeing_controversy':
        # Not derivable from the numeric model; treat as unconstrained so the run
        # still produces outcomes. The narrative layer owns this scenario.
        return lambda r: True

    # Unknown condition type: do not reject anything.
    return lambda rollout: True
