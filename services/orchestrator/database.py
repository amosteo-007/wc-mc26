"""PostgreSQL + Redis operations for orchestrator."""
import os
import json
import uuid
import psycopg2
from psycopg2.extras import RealDictCursor
import redis
from typing import Dict, Optional, List

from knockout import resolve_bracket

POSTGRES_URL = os.getenv(
    'POSTGRES_URL',
    'postgresql://wc2026:wc2026_dev@localhost:5432/wc2026'
)
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379')

_redis = None


def get_redis() -> redis.Redis:
    global _redis
    if _redis is None:
        _redis = redis.from_url(REDIS_URL, decode_responses=True)
    return _redis


def get_pg_conn():
    return psycopg2.connect(POSTGRES_URL, cursor_factory=RealDictCursor)


# Pinned for reproducibility: data snapshot date + authored-pack version.
# Bump when ratings/seeds or pack content change (CLAUDE.md data-versioning rule).
DATA_VERSION = os.getenv('DATA_VERSION', '2026-06-01+packs-v1')


def create_run(
    mode: str, condition: Optional[Dict], packs: List[str],
    audience: List[str], tier: str, n_runs: int = 10000
) -> str:
    """Create a new simulation run. Returns run_id."""
    run_id = str(uuid.uuid4())
    with get_pg_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO sim_runs
                    (id, mode, condition, packs, audience, tier, n_runs,
                     data_version, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'queued')
            """, (
                run_id, mode,
                json.dumps(condition) if condition else None,
                json.dumps(packs), json.dumps(audience), tier, n_runs,
                DATA_VERSION
            ))
        conn.commit()

    r = get_redis()
    r.hset(f"job:{run_id}", mapping={
        'status': 'queued', 'mode': mode, 'tier': tier,
        'created_at': str(os.environ.get('START_TIME', ''))
    })
    return run_id


def get_run(run_id: str) -> Optional[Dict]:
    """Get run details. A non-UUID id (e.g. the static-export shell's "_"
    placeholder) is treated as 'not found' rather than crashing the uuid cast."""
    try:
        uuid.UUID(str(run_id))
    except (ValueError, TypeError, AttributeError):
        return None
    with get_pg_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM sim_runs WHERE id = %s", (run_id,))
            return cur.fetchone()


def get_teams() -> List[Dict]:
    """All tournament teams (single source of truth for the wizard dropdown)."""
    with get_pg_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT fifa_code, name, confederation FROM teams ORDER BY name"
            )
            return cur.fetchall()


def get_tournament_state(edition: str = 'WC2026') -> Dict:
    """Return the official groups, computed live standings, and the knockout
    bracket (TBD until the group stage completes). Powers the wizard's
    tournament view in step 3.
    """
    with get_pg_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT spec FROM tournament_format WHERE edition = %s",
                (edition,)
            )
            row = cur.fetchone()
            spec = row['spec'] if row else {}

            cur.execute(
                "SELECT name, fifa_code FROM teams"
            )
            name_by_code = {r['fifa_code']: r['name'] for r in cur.fetchall()}

            cur.execute("""
                SELECT group_name, matchday, home_code, away_code,
                       home_goals, away_goals, played_on
                FROM wc_results
                WHERE edition = %s AND stage = 'group'
                ORDER BY group_name, matchday
            """, (edition,))
            results = cur.fetchall()

            cur.execute("""
                SELECT stage, matchday, home_code, away_code,
                       home_goals, away_goals, shootout_winner, played_on
                FROM wc_results
                WHERE edition = %s AND stage <> 'group'
                ORDER BY stage, matchday
            """, (edition,))
            ko_results = cur.fetchall()

    return _assemble_groups(spec, name_by_code, results, ko_results)


def _assemble_groups(
    spec: Dict, name_by_code: Dict, results: List[Dict],
    ko_results: Optional[List[Dict]] = None,
) -> Dict:
    """Compute group standings (FIFA order) from results and pair with fixtures."""
    results_by_group: Dict[str, List[Dict]] = {}
    for r in results:
        results_by_group.setdefault(r['group_name'], []).append(r)

    groups_out = []
    for g in spec.get('groups', []):
        gname, codes = g['group'], g['teams']
        stats = {
            c: {'team': c, 'name': name_by_code.get(c, c),
                'p': 0, 'w': 0, 'd': 0, 'l': 0, 'gf': 0, 'ga': 0, 'pts': 0}
            for c in codes
        }
        matches = []
        for r in results_by_group.get(gname, []):
            h, a, hg, ag = r['home_code'], r['away_code'], r['home_goals'], r['away_goals']
            for code, gf, ga in ((h, hg, ag), (a, ag, hg)):
                s = stats.get(code)
                if not s:
                    continue
                s['p'] += 1
                s['gf'] += gf
                s['ga'] += ga
                if gf > ga:
                    s['w'] += 1
                    s['pts'] += 3
                elif gf == ga:
                    s['d'] += 1
                    s['pts'] += 1
                else:
                    s['l'] += 1
            matches.append({
                'home': h, 'away': a, 'home_goals': hg, 'away_goals': ag,
                'matchday': r['matchday'],
                'played_on': str(r['played_on']) if r['played_on'] else None,
            })

        standings = sorted(
            stats.values(),
            key=lambda s: (-s['pts'], -(s['gf'] - s['ga']), -s['gf'], s['team'])
        )
        for i, s in enumerate(standings):
            s['gd'] = s['gf'] - s['ga']
            s['rank'] = i + 1
        groups_out.append({
            'group': gname,
            'standings': standings,
            'matches': matches,
            'played': len(matches),
        })

    group_stage_complete = all(grp['played'] >= 6 for grp in groups_out)

    # Resolve the knockout bracket forward from real results: group winners/
    # runners-up + best thirds feed R32, and each knockout result advances the
    # winner into the next round. Unresolved slots stay None (TBD) so the UI can
    # render placeholders until the feeder match is played.
    standings_by_name = {grp['group']: grp['standings'] for grp in groups_out}
    resolved_bracket = resolve_bracket(
        spec.get('knockout_bracket', {}),
        standings_by_name,
        ko_results or [],
    )

    return {
        'edition': spec.get('edition', 'WC2026'),
        'groups': groups_out,
        # The authored placeholder bracket (back-compat) plus the resolved one.
        'knockout_bracket': spec.get('knockout_bracket', {}),
        'knockout': resolved_bracket,
        'group_stage_complete': group_stage_complete,
        'champion': resolved_bracket.get('champion'),
    }


def update_run_status(run_id: str, status: str) -> None:
    """Update run status."""
    with get_pg_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE sim_runs SET status = %s WHERE id = %s",
                (status, run_id)
            )
        conn.commit()
    r = get_redis()
    r.hset(f"job:{run_id}", "status", status)


def get_job_status(run_id: str) -> Dict:
    """Get job status from Redis."""
    r = get_redis()
    data = r.hgetall(f"job:{run_id}")
    return data if data else {'status': 'unknown'}
