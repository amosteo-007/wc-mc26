"""Ingest live WC2026 match results into wc_results (orchestrator-local copy).

The orchestrator deploys standalone (rootDir = services/orchestrator), so it
can't import the repo-root ``pipeline`` package. This module is the self-
contained ingest used by the ``POST /admin/refresh`` endpoint: it accepts either
a results payload posted directly (manual entry) or pulls one from a configured
feed URL / the FIFA adapter, validates each match, and idempotently upserts.

Payload shape (same as pipeline.ingest.wc_results)::

    {"edition": "WC2026", "matches": [
       {"stage": "group", "group": "A", "matchday": 1,
        "home": "MEX", "away": "RSA", "home_goals": 2, "away_goals": 0,
        "shootout_winner": null, "played_on": "2026-06-11"}, ...]}

Only *played* matches (both goal fields present) are written; unplayed fixtures
are skipped so they stay TBD.
"""
import os
from typing import Dict, List, Optional, Tuple

import httpx

import database as db

WC_RESULTS_URL = os.getenv('WC_RESULTS_URL')
WC_RESULTS_SOURCE = os.getenv('WC_RESULTS_SOURCE', '').lower()  # '' | 'fifa'
FETCH_TIMEOUT = float(os.getenv('WC_RESULTS_TIMEOUT', '20'))

VALID_STAGES = {'group', 'R32', 'R16', 'QF', 'SF', '3rd_place', 'Final'}
_STAGE_ALIASES = {
    'final': 'Final', 'FINAL': 'Final',
    '3rd': '3rd_place', 'third_place': '3rd_place', '3rd-place': '3rd_place',
    'R64': 'R32',
}


def _coerce_match(raw: Dict) -> Optional[Tuple]:
    """Validate one match dict into a row tuple, or None to skip it."""
    home, away = raw.get('home'), raw.get('away')
    hg, ag = raw.get('home_goals'), raw.get('away_goals')
    if not home or not away or hg is None or ag is None:
        return None

    stage = _STAGE_ALIASES.get(raw.get('stage', 'group'), raw.get('stage', 'group'))
    if stage not in VALID_STAGES:
        return None
    try:
        hg, ag = int(hg), int(ag)
    except (TypeError, ValueError):
        return None
    if hg < 0 or ag < 0:
        return None

    matchday = raw.get('matchday')
    try:
        matchday = int(matchday) if matchday is not None else None
    except (TypeError, ValueError):
        matchday = None

    shootout = raw.get('shootout_winner')
    shootout = str(shootout).upper() if shootout else None

    return (
        stage, raw.get('group'), matchday,
        str(home).upper(), str(away).upper(), hg, ag, shootout,
        raw.get('played_on'),
    )


def _upsert(rows: List[Tuple], edition: str) -> int:
    if not rows:
        return 0
    with db.get_pg_conn() as conn:
        with conn.cursor() as cur:
            for r in rows:
                cur.execute(
                    """
                    INSERT INTO wc_results
                        (edition, stage, group_name, matchday,
                         home_code, away_code, home_goals, away_goals,
                         shootout_winner, played_on)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (edition, stage, home_code, away_code)
                    DO UPDATE SET
                        group_name      = EXCLUDED.group_name,
                        matchday        = EXCLUDED.matchday,
                        home_goals      = EXCLUDED.home_goals,
                        away_goals      = EXCLUDED.away_goals,
                        shootout_winner = EXCLUDED.shootout_winner,
                        played_on       = EXCLUDED.played_on
                    """,
                    (edition, *r),
                )
        conn.commit()
    return len(rows)


def _fetch_payload() -> Dict:
    """Pull a results payload from the configured source.

    WC_RESULTS_SOURCE=fifa uses the FIFA adapter; otherwise WC_RESULTS_URL is
    fetched as raw JSON in our shape. Raises if neither is configured.
    """
    if WC_RESULTS_SOURCE == 'fifa':
        from fifa_adapter import fetch_results  # local, lazy (optional dep path)
        return fetch_results()
    if WC_RESULTS_URL:
        resp = httpx.get(WC_RESULTS_URL, timeout=FETCH_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    raise RuntimeError(
        'No results source configured: set WC_RESULTS_SOURCE=fifa or '
        'WC_RESULTS_URL, or POST a {edition, matches:[...]} body.'
    )


def refresh(payload: Optional[Dict] = None) -> Dict:
    """Upsert results from ``payload`` (manual) or the configured feed.

    Returns a small summary dict for the endpoint to echo back.
    """
    if payload is None:
        payload = _fetch_payload()
    edition = payload.get('edition', 'WC2026')
    raw_matches = payload.get('matches', [])
    rows = [r for r in (_coerce_match(m) for m in raw_matches) if r]
    written = _upsert(rows, edition)
    return {
        'edition': edition,
        'received': len(raw_matches),
        'written': written,
        'skipped': len(raw_matches) - written,
    }
