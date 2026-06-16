"""Daily fetcher for live 2026 World Cup match results.

Pulls the current results from a configurable JSON endpoint (``WC_RESULTS_URL``)
and upserts them into the ``wc_results`` table. Designed to run once a day; the
upsert is idempotent (``ON CONFLICT`` on the natural key updates the score in
place), so re-running after new matches simply refreshes the standings the
wizard's tournament view reads.

Expected JSON shape from ``WC_RESULTS_URL``::

    {
      "edition": "WC2026",
      "matches": [
        {
          "stage": "group",        # group | R32 | R16 | QF | SF | final
          "group": "A",            # 'A'..'L' for group matches, null otherwise
          "matchday": 1,            # 1..3 in the group stage, null otherwise
          "home": "MEX",           # FIFA code
          "away": "RSA",
          "home_goals": 2,
          "away_goals": 0,
          "played_on": "2026-06-11" # ISO date or null if not yet played
        }
      ]
    }

Only *played* matches (both goal fields present) are written. Unplayed fixtures
are skipped so they keep showing as TBD until a real score lands.
"""
import os
import sys
from typing import Dict, List, Optional, Tuple

import httpx
import psycopg2

POSTGRES_URL = os.getenv(
    'POSTGRES_URL',
    'postgresql://wc2026:wc2026_dev@localhost:5432/wc2026',
)
WC_RESULTS_URL = os.getenv('WC_RESULTS_URL')
FETCH_TIMEOUT = float(os.getenv('WC_RESULTS_TIMEOUT', '20'))

VALID_STAGES = {'group', 'R32', 'R16', 'QF', 'SF', 'final'}


def fetch_payload(url: str) -> Dict:
    """GET the results JSON. Raises on a non-2xx response or invalid JSON."""
    resp = httpx.get(url, timeout=FETCH_TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def _coerce_match(raw: Dict) -> Optional[Tuple]:
    """Validate one match record into a row tuple, or None to skip it.

    A match is skipped (not an error) when it has no score yet or is missing a
    required field — those simply stay TBD in the tournament view.
    """
    home = raw.get('home')
    away = raw.get('away')
    hg = raw.get('home_goals')
    ag = raw.get('away_goals')
    if not home or not away or hg is None or ag is None:
        return None

    stage = raw.get('stage', 'group')
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

    return (
        stage,
        raw.get('group'),
        matchday,
        str(home).upper(),
        str(away).upper(),
        hg,
        ag,
        raw.get('played_on'),
    )


def upsert_results(rows: List[Tuple], edition: str) -> int:
    """Idempotently upsert validated rows. Returns the number written."""
    if not rows:
        return 0
    with psycopg2.connect(POSTGRES_URL) as conn:
        with conn.cursor() as cur:
            for r in rows:
                cur.execute(
                    """
                    INSERT INTO wc_results
                        (edition, stage, group_name, matchday,
                         home_code, away_code, home_goals, away_goals, played_on)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (edition, stage, home_code, away_code)
                    DO UPDATE SET
                        group_name = EXCLUDED.group_name,
                        matchday   = EXCLUDED.matchday,
                        home_goals = EXCLUDED.home_goals,
                        away_goals = EXCLUDED.away_goals,
                        played_on  = EXCLUDED.played_on
                    """,
                    (edition, *r),
                )
        conn.commit()
    return len(rows)


def refresh(url: Optional[str] = None) -> int:
    """Fetch from ``url`` (or ``WC_RESULTS_URL``) and upsert. Returns row count.

    Raises ``RuntimeError`` if no URL is configured so the scheduler logs a
    clear message instead of silently doing nothing.
    """
    url = url or WC_RESULTS_URL
    if not url:
        raise RuntimeError(
            'WC_RESULTS_URL is not set — point it at a JSON results feed '
            '(see module docstring for the expected shape).'
        )
    payload = fetch_payload(url)
    edition = payload.get('edition', 'WC2026')
    rows = [r for r in (_coerce_match(m) for m in payload.get('matches', [])) if r]
    written = upsert_results(rows, edition)
    return written


def main() -> int:
    try:
        n = refresh()
    except Exception as exc:  # noqa: BLE001 — top-level CLI guard, log and exit
        print(f'[wc-results] refresh failed: {exc}', file=sys.stderr)
        return 1
    print(f'[wc-results] upserted {n} played match(es)')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
