"""Adapter for FIFA's public data API (api.fifa.com/api/v3).

Maps the WC2026 match calendar into our results shape
(``{edition, matches:[...]}``) consumed by ``results_refresh.refresh``.

IMPORTANT: ``api.fifa.com`` is undocumented and unofficial. It powers FIFA's
own site but is not a supported product — field names or availability can change
without notice. So this adapter is deliberately defensive: anything it can't
parse is skipped (never raises mid-match), and the ``/admin/refresh`` endpoint
always supports a manual JSON fallback if FIFA changes the API.

Discovered identifiers (2026 edition):
    IdCompetition = 17       # FIFA World Cup
    IdSeason      = 285023   # FIFA World Cup 2026
"""
import os
from typing import Dict, List, Optional

import httpx

FIFA_BASE = os.getenv('FIFA_API_BASE', 'https://api.fifa.com/api/v3')
FIFA_COMPETITION = os.getenv('FIFA_COMPETITION_ID', '17')
FIFA_SEASON = os.getenv('FIFA_SEASON_ID', '285023')
FETCH_TIMEOUT = float(os.getenv('WC_RESULTS_TIMEOUT', '25'))
# Page size for the calendar endpoint; 104 covers the whole tournament.
PAGE_COUNT = int(os.getenv('FIFA_PAGE_COUNT', '150'))

# MatchStatus values that mean the result is final. FIFA uses 0=upcoming,
# 3=played; live/abandoned states vary. We additionally require real scores, so
# this set is a guard, not the sole signal.
_PLAYED_STATUSES = {0, 1, 3}  # tolerant: scores presence is the real gate

# StageName.Description → our stage vocabulary. Matched case-insensitively on a
# normalized substring so minor wording changes ("Round of 16" vs "Last 16")
# still land. Order matters: check more specific labels first.
_STAGE_MAP = [
    ('round of 32', 'R32'),
    ('round of 16', 'R16'),
    ('last 16', 'R16'),
    ('quarter', 'QF'),
    ('semi', 'SF'),
    ('third place', '3rd_place'),
    ('3rd place', '3rd_place'),
    ('play-off for third', '3rd_place'),
    ('final', 'Final'),       # after 'semi'/'quarter' so it doesn't shadow them
    ('first stage', 'group'),
    ('group', 'group'),
]


def _localized(field) -> str:
    """Pull the English description out of FIFA's localized-array fields."""
    if isinstance(field, list) and field:
        return str(field[0].get('Description', '') or '')
    if isinstance(field, str):
        return field
    return ''


def _map_stage(stage_name: str) -> Optional[str]:
    s = stage_name.strip().lower()
    for needle, stage in _STAGE_MAP:
        if needle in s:
            return stage
    return None


def _map_group(group_name: str) -> Optional[str]:
    """'Group A' → 'A'. Returns None for non-group rounds."""
    g = group_name.strip()
    if g.lower().startswith('group') and len(g.split()) >= 2:
        return g.split()[-1].upper()
    return None


def _to_int(v) -> Optional[int]:
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _map_match(m: Dict) -> Optional[Dict]:
    """Map one FIFA match object to our shape, or None to skip it."""
    home = m.get('Home') or {}
    away = m.get('Away') or {}
    home_code = home.get('IdCountry')
    away_code = away.get('IdCountry')
    if not home_code or not away_code:
        return None  # TBD knockout slot or malformed — skip

    hg = _to_int(m.get('HomeTeamScore'))
    ag = _to_int(m.get('AwayTeamScore'))
    status = m.get('MatchStatus')
    # Only emit genuinely played matches: both scores present. (Upcoming games
    # have null scores; downstream coercion also skips Nones, so this is belt
    # and suspenders.)
    if hg is None or ag is None:
        return None
    if status is not None and status not in _PLAYED_STATUSES:
        return None

    stage = _map_stage(_localized(m.get('StageName')))
    if stage is None:
        return None
    group = _map_group(_localized(m.get('GroupName'))) if stage == 'group' else None

    matchday = _to_int(m.get('MatchDay'))

    # Shootout winner: FIFA's `Winner` is a team id, not a country code, and only
    # matters when the 90'/ET score is level. Resolve it to the country code.
    shootout = None
    if stage != 'group' and hg == ag:
        winner_id = m.get('Winner')
        if winner_id and str(winner_id) == str(home.get('IdTeam')):
            shootout = home_code
        elif winner_id and str(winner_id) == str(away.get('IdTeam')):
            shootout = away_code

    played_on = (m.get('Date') or m.get('LocalDate') or '')[:10] or None

    return {
        'stage': stage,
        'group': group,
        'matchday': matchday,
        'home': home_code,
        'away': away_code,
        'home_goals': hg,
        'away_goals': ag,
        'shootout_winner': shootout,
        'played_on': played_on,
    }


def fetch_results() -> Dict:
    """Fetch WC2026 matches from FIFA and return them in our results shape.

    Raises on a transport/HTTP failure (the caller logs and returns 502); a
    malformed individual match is skipped, not fatal.
    """
    url = f"{FIFA_BASE}/calendar/matches"
    params = {
        'idCompetition': FIFA_COMPETITION,
        'idSeason': FIFA_SEASON,
        'language': 'en',
        'count': PAGE_COUNT,
    }
    resp = httpx.get(url, params=params, timeout=FETCH_TIMEOUT)
    resp.raise_for_status()
    data = resp.json()

    matches: List[Dict] = []
    for raw in data.get('Results', []) or []:
        try:
            mapped = _map_match(raw)
        except Exception:  # noqa: BLE001 — one bad row must not sink the batch
            mapped = None
        if mapped:
            matches.append(mapped)

    return {'edition': 'WC2026', 'matches': matches}
