"""Blend multiple rating sources into a single strength prior.

Single documented function so it can be A/B tested.
"""
from typing import Dict, Optional


def blend_ratings(
    elo: Optional[float] = None,
    spi: Optional[float] = None,
    market_implied: Optional[float] = None,
    weights: Optional[Dict[str, float]] = None
) -> float:
    """Blend available ratings into a single strength estimate.

    Default weights: Elo 0.6, SPI 0.2, Market 0.2.
    Falls back to Elo-only if no other sources.

    >>> blend_ratings(elo=2000)
    2000.0
    >>> blend_ratings(elo=2000, spi=1950)
    1990.0
    """
    if weights is None:
        weights = {'elo': 0.6, 'spi': 0.2, 'market': 0.2}

    total_weight = 0.0
    blended = 0.0

    if elo is not None:
        blended += elo * weights.get('elo', 0.6)
        total_weight += weights.get('elo', 0.6)

    if spi is not None:
        blended += spi * weights.get('spi', 0.2)
        total_weight += weights.get('spi', 0.2)

    if market_implied is not None:
        blended += market_implied * weights.get('market', 0.2)
        total_weight += weights.get('market', 0.2)

    if total_weight == 0:
        return 1800.0

    return blended / total_weight


def blend_team_ratings(
    team_ratings: Dict[str, Dict[str, float]],
    weights: Optional[Dict[str, float]] = None
) -> Dict[str, float]:
    """Blend ratings for multiple teams.

    Args:
        team_ratings: {team_code: {source: rating}}
        weights: Optional source weights

    Returns:
        {team_code: blended_rating}
    """
    result = {}
    for team, sources in team_ratings.items():
        result[team] = blend_ratings(
            elo=sources.get('eloratings.net'),
            spi=sources.get('spi'),
            market_implied=sources.get('market'),
            weights=weights
        )
    return result
