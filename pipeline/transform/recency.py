"""Recency-weighting for historical match results.

Weight function: exponential decay with configurable half-life.
Qualifier-era matches receive an additional boost.
"""
import math
from datetime import date, datetime
from typing import List, Dict, Optional

DEFAULT_HALF_LIFE_DAYS = 730  # 2 years
QUALIFIER_BOOST = 1.5  # multiplier for qualifier matches


def compute_recency_weight(
    match_date: date,
    reference_date: Optional[date] = None,
    half_life_days: int = DEFAULT_HALF_LIFE_DAYS,
    competition: Optional[str] = None
) -> float:
    """Compute recency weight for a match.

    Uses exponential decay: weight = 2^(-age/half_life).
    Qualifier matches get a boost multiplier.

    >>> from datetime import date
    >>> compute_recency_weight(date(2026, 6, 1), date(2026, 6, 1))
    1.0
    >>> w = compute_recency_weight(date(2024, 6, 1), date(2026, 6, 1))
    >>> 0.49 < w < 0.51
    True
    """
    if reference_date is None:
        reference_date = date.today()

    if isinstance(match_date, str):
        match_date = date.fromisoformat(match_date[:10])

    age_days = (reference_date - match_date).days
    if age_days < 0:
        age_days = 0

    weight = 2.0 ** (-age_days / half_life_days)

    if competition and 'qualif' in competition.lower():
        weight *= QUALIFIER_BOOST

    return weight


def weight_matches(
    matches: List[Dict],
    reference_date: Optional[date] = None,
    half_life_days: int = DEFAULT_HALF_LIFE_DAYS
) -> List[Dict]:
    """Apply recency weights to a list of matches.

    Each match gets a 'recency_weight' field added.
    """
    if reference_date is None:
        reference_date = date.today()

    for match in matches:
        match_date = match.get('date', '2020-01-01')
        if isinstance(match_date, str):
            match_date = date.fromisoformat(match_date[:10])

        match['recency_weight'] = compute_recency_weight(
            match_date=match_date,
            reference_date=reference_date,
            half_life_days=half_life_days,
            competition=match.get('competition')
        )

    return matches
