"""PostgreSQL database operations for outcome engine."""
import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import List, Dict, Optional

POSTGRES_URL = os.getenv(
    'POSTGRES_URL',
    'postgresql://wc2026:wc2026_dev@localhost:5432/wc2026'
)


def get_connection():
    """Get a database connection with RealDictCursor."""
    return psycopg2.connect(POSTGRES_URL, cursor_factory=RealDictCursor)


def get_teams() -> List[Dict]:
    """Fetch all teams."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, fifa_code, name, confederation FROM teams ORDER BY name"
            )
            return cur.fetchall()


def get_ratings(as_of: str = '2026-06-01') -> List[Dict]:
    """Fetch latest ratings for all teams as of given date."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT DISTINCT ON (team_id) team_id, source, rating, as_of
                FROM ratings WHERE as_of <= %s
                ORDER BY team_id, (source = 'blended') DESC, as_of DESC
            """, (as_of,))
            return cur.fetchall()


def get_format(edition: str = 'WC2026') -> Optional[Dict]:
    """Fetch tournament format spec."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT spec FROM tournament_format WHERE edition = %s",
                (edition,)
            )
            row = cur.fetchone()
            return row['spec'] if row else None


def save_results(run_id: str, results: Dict) -> None:
    """Save outcome results to database."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO outcome_results
                    (run_id, champion_probs, finalist_probs, top_paths, confidence)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (run_id) DO UPDATE
                SET champion_probs = EXCLUDED.champion_probs,
                    finalist_probs = EXCLUDED.finalist_probs,
                    top_paths = EXCLUDED.top_paths,
                    confidence = EXCLUDED.confidence
            """, (
                run_id,
                json.dumps(results.get('champion_probs', {})),
                json.dumps(results.get('finalist_probs', {})),
                json.dumps(results.get('top_paths', [])),
                json.dumps(results.get('confidence', {}))
            ))
        conn.commit()


def get_recent_matches(
    team_codes: List[str],
    since_date: str = '2023-01-01',
    limit: int = 500
) -> List[Dict]:
    """Fetch recent match results for the given teams.

    Used by the simulator to compute form adjustments on top of
    base Elo ratings. Returns matches where both home and away
    are among the qualified teams.

    Each row: {home_team, away_team, home_goals, away_goals,
               match_date, competition, neutral}
    """
    if not team_codes:
        return []

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    h.fifa_code AS home_team,
                    a.fifa_code AS away_team,
                    m.home_goals,
                    m.away_goals,
                    m.match_date,
                    m.competition,
                    m.neutral
                FROM matches_history m
                JOIN teams h ON h.id = m.home_id
                JOIN teams a ON a.id = m.away_id
                WHERE h.fifa_code = ANY(%s)
                  AND a.fifa_code = ANY(%s)
                  AND m.match_date >= %s::date
                ORDER BY m.match_date DESC
                LIMIT %s
            """, (team_codes, team_codes, since_date, limit))
            return cur.fetchall()


def get_team_by_code(fifa_code: str) -> Optional[Dict]:
    """Fetch a single team by FIFA code. Returns None if not found."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, fifa_code, name, confederation FROM teams WHERE fifa_code = %s",
                (fifa_code,)
            )
            return cur.fetchone()


def get_matches_for_teams(
    team_codes: List[str],
    since_date: str = '2023-01-01',
    limit: int = 500
) -> List[Dict]:
    """Fetch matches where EITHER home OR away is among team_codes.

    Unlike get_recent_matches (which requires BOTH teams in the list),
    this returns any match involving at least one of the given teams,
    so form can be computed even when teams haven't played each other.
    Same row shape as get_recent_matches.
    """
    if not team_codes:
        return []

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    h.fifa_code AS home_team,
                    a.fifa_code AS away_team,
                    m.home_goals,
                    m.away_goals,
                    m.match_date,
                    m.competition,
                    m.neutral
                FROM matches_history m
                JOIN teams h ON h.id = m.home_id
                JOIN teams a ON a.id = m.away_id
                WHERE (h.fifa_code = ANY(%s) OR a.fifa_code = ANY(%s))
                  AND m.match_date >= %s::date
                ORDER BY m.match_date DESC
                LIMIT %s
            """, (team_codes, team_codes, since_date, limit))
            return cur.fetchall()


def get_data_version() -> Dict:
    """Return a summary of what data the simulation is running on.

    Used to stamp sim_runs for reproducibility.
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT MAX(as_of) AS latest_rating FROM ratings"
            )
            rating_date = cur.fetchone()['latest_rating']

            cur.execute(
                "SELECT COUNT(*) AS cnt FROM matches_history"
            )
            match_count = cur.fetchone()['cnt']

            cur.execute(
                "SELECT COUNT(*) AS cnt FROM teams"
            )
            team_count = cur.fetchone()['cnt']

    return {
        'teams': team_count,
        'ratings_as_of': str(rating_date) if rating_date else None,
        'matches_available': match_count,
        'snapshot_at': __import__('datetime').datetime.now().isoformat()
    }
