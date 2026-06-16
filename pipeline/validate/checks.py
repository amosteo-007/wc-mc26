"""Data quality gates — confidence flags are born here."""
from typing import Dict, List, Optional
from datetime import date, datetime


def check_coverage(
    teams: List[Dict], ratings: List[Dict], required_teams: int = 48
) -> Dict:
    """Check that every qualified team has a current rating."""
    rated_team_ids = {r['team_id'] for r in ratings}
    missing = [t for t in teams if t['id'] not in rated_team_ids]

    return {
        'passed': len(missing) == 0,
        'missing_teams': [t['fifa_code'] for t in missing],
        'coverage_pct': (
            (len(teams) - len(missing)) / max(len(teams), 1) * 100
        ),
        'required': required_teams,
        'actual': len(teams) - len(missing)
    }


def check_freshness(
    ratings: List[Dict],
    max_age_days: int = 30,
    reference_date: Optional[date] = None
) -> Dict:
    """Check rating freshness."""
    if reference_date is None:
        reference_date = date.today()

    stale = []
    for r in ratings:
        as_of = r.get('as_of')
        if isinstance(as_of, str):
            as_of = date.fromisoformat(as_of[:10])

        age = (reference_date - as_of).days
        if age > max_age_days:
            stale.append(r['team_id'])

    return {
        'passed': len(stale) == 0,
        'stale_count': len(stale),
        'max_age_days': max_age_days,
        'total_rated': len(ratings)
    }


def check_schema(matches: List[Dict]) -> Dict:
    """Validate match data schema: types, non-null keys, score sanity."""
    errors = []

    for i, match in enumerate(matches):
        if not match.get('home_team'):
            errors.append(f"Match {i}: missing home_team")
        if not match.get('away_team'):
            errors.append(f"Match {i}: missing away_team")

        hg = match.get('home_goals')
        ag = match.get('away_goals')

        if hg is None or not isinstance(hg, (int, float)):
            errors.append(f"Match {i}: invalid home_goals")
        elif hg < 0 or hg > 30:
            errors.append(f"Match {i}: implausible home_goals={hg}")

        if ag is None or not isinstance(ag, (int, float)):
            errors.append(f"Match {i}: invalid away_goals")
        elif ag < 0 or ag > 30:
            errors.append(f"Match {i}: implausible away_goals={ag}")

    return {
        'passed': len(errors) == 0,
        'errors': errors[:20],
        'total_checked': len(matches)
    }


def check_cross_source_consistency(
    team_ratings: Dict[str, Dict[str, float]],
    max_disagreement: float = 150.0
) -> Dict:
    """Check rating agreement across sources."""
    flags = []

    for team, sources in team_ratings.items():
        values = list(sources.values())
        if len(values) >= 2:
            range_val = max(values) - min(values)
            if range_val > max_disagreement:
                flags.append({
                    'team': team,
                    'disagreement': range_val,
                    'sources': sources
                })

    return {
        'passed': len(flags) == 0,
        'flagged_teams': flags,
        'threshold': max_disagreement
    }


def run_all_checks(
    teams: List[Dict],
    ratings: List[Dict],
    matches: List[Dict],
    team_ratings_by_source: Optional[Dict[str, Dict[str, float]]] = None
) -> Dict:
    """Run all quality checks and produce confidence report."""
    checks = {
        'coverage': check_coverage(teams, ratings),
        'freshness': check_freshness(ratings),
        'schema': check_schema(matches),
    }

    if team_ratings_by_source:
        checks['cross_source'] = check_cross_source_consistency(
            team_ratings_by_source
        )

    all_passed = all(c.get('passed', False) for c in checks.values())

    return {
        'passed': all_passed,
        'checks': checks,
        'confidence': 'high' if all_passed else 'medium',
        'checked_at': datetime.now().isoformat()
    }
