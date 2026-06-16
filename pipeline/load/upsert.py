"""Idempotent upsert functions for all tables."""
import json
import os
import psycopg2
from psycopg2.extras import execute_values
from typing import List, Dict

POSTGRES_URL = os.getenv(
    'POSTGRES_URL',
    'postgresql://wc2026:wc2026_dev@localhost:5432/wc2026'
)


def get_conn():
    return psycopg2.connect(POSTGRES_URL)


def upsert_teams(teams: List[Dict]) -> int:
    """Insert or ignore teams by fifa_code."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            execute_values(cur, """
                INSERT INTO teams (fifa_code, name, confederation)
                VALUES %s
                ON CONFLICT (fifa_code) DO UPDATE
                SET name = EXCLUDED.name,
                    confederation = EXCLUDED.confederation
            """, [
                (t['fifa_code'], t['name'], t.get('confederation', ''))
                for t in teams
            ])
        conn.commit()
    return len(teams)


def upsert_ratings(ratings: List[Dict]) -> int:
    """Insert ratings (idempotent by team_id, source, as_of)."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            execute_values(cur, """
                INSERT INTO ratings (team_id, source, rating, as_of)
                SELECT t.id, v.source, v.rating, v.as_of::date
                FROM (VALUES %s) AS v(fifa_code, source, rating, as_of)
                JOIN teams t ON t.fifa_code = v.fifa_code
                ON CONFLICT (team_id, source, as_of) DO UPDATE
                SET rating = EXCLUDED.rating
            """, [
                (r['fifa_code'], r['source'], r['rating'], r['as_of'])
                for r in ratings
            ])
        conn.commit()
    return len(ratings)


def upsert_matches(matches: List[Dict]) -> int:
    """Insert historical matches."""
    inserted = 0
    with get_conn() as conn:
        with conn.cursor() as cur:
            for m in matches:
                cur.execute("""
                    INSERT INTO matches_history
                    (match_date, home_id, away_id, home_goals, away_goals,
                     competition, neutral)
                    SELECT %s::date, h.id, a.id, %s, %s, %s, %s
                    FROM teams h, teams a
                    WHERE h.fifa_code = %s AND a.fifa_code = %s
                    ON CONFLICT DO NOTHING
                """, (
                    m.get('date', '2024-01-01'),
                    m.get('home_goals', 0), m.get('away_goals', 0),
                    m.get('competition', 'friendly'),
                    m.get('neutral', False),
                    m.get('home_team'), m.get('away_team')
                ))
                inserted += cur.rowcount
        conn.commit()
    return inserted


def upsert_packs(packs: List[Dict]) -> int:
    """Insert context packs (versioned — insert, never overwrite)."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            execute_values(cur, """
                INSERT INTO context_packs (pack_type, entity_key, version, payload)
                VALUES %s
            """, [
                (p['pack_type'], p.get('entity_key'), p.get('version', 1),
                 json.dumps(p.get('payload', {})))
                for p in packs
            ])
        conn.commit()
    return len(packs)
