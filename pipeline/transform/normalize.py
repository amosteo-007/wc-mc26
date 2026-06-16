"""Normalize team identities and deduplicate match results.

All team references are normalized to FIFA three-letter codes.
"""
from typing import Dict, List, Optional, Set, Tuple

NAME_TO_FIFA: Dict[str, str] = {
    'united states': 'USA', 'usa': 'USA', 'usmnt': 'USA',
    'mexico': 'MEX', 'canada': 'CAN',
    'argentina': 'ARG', 'brazil': 'BRA', 'uruguay': 'URU',
    'ecuador': 'ECU', 'colombia': 'COL', 'peru': 'PER', 'chile': 'CHI',
    'england': 'ENG', 'france': 'FRA', 'germany': 'GER',
    'spain': 'ESP', 'portugal': 'POR', 'netherlands': 'NED',
    'belgium': 'BEL', 'italy': 'ITA', 'croatia': 'CRO',
    'denmark': 'DEN', 'switzerland': 'SUI', 'serbia': 'SRB',
    'poland': 'POL', 'ukraine': 'UKR', 'sweden': 'SWE',
    'wales': 'WAL', 'scotland': 'SCO', 'austria': 'AUT',
    'czech republic': 'CZE', 'czechia': 'CZE',
    'turkey': 'TUR', 'hungary': 'HUN',
    'japan': 'JPN', 'south korea': 'KOR', 'korea republic': 'KOR',
    'iran': 'IRN', 'saudi arabia': 'KSA', 'australia': 'AUS',
    'united arab emirates': 'UAE', 'uae': 'UAE', 'qatar': 'QAT',
    'morocco': 'MAR', 'senegal': 'SEN', 'tunisia': 'TUN',
    'algeria': 'ALG', 'egypt': 'EGY', 'nigeria': 'NGA',
    'ghana': 'GHA', 'cameroon': 'CMR', 'ivory coast': 'CIV',
    "côte d'ivoire": 'CIV', 'south africa': 'RSA',
    'new zealand': 'NZL',
}


def normalize_team_name(name: str) -> Optional[str]:
    """Convert a team name to its FIFA code.

    Tries exact match, then lowercase match, then partial match.
    Returns None if no mapping found.

    >>> normalize_team_name('Brazil')
    'BRA'
    >>> normalize_team_name('United States')
    'USA'
    """
    if not name:
        return None

    upper = name.strip().upper()
    if len(upper) == 3 and upper in set(NAME_TO_FIFA.values()):
        return upper

    lower = name.strip().lower()
    if lower in NAME_TO_FIFA:
        return NAME_TO_FIFA[lower]

    for key, code in NAME_TO_FIFA.items():
        if key in lower or lower in key:
            return code

    return None


def normalize_match(match: Dict) -> Optional[Dict]:
    """Normalize a single match record.

    Returns normalized dict with fifa_codes, or None if teams can't be mapped.
    """
    home_code = normalize_team_name(match.get('home_team', ''))
    away_code = normalize_team_name(match.get('away_team', ''))

    if not home_code or not away_code:
        return None

    return {
        'home_team': home_code,
        'away_team': away_code,
        'home_goals': int(match.get('home_goals', 0)),
        'away_goals': int(match.get('away_goals', 0)),
        'date': match.get('date'),
        'competition': match.get('competition', 'friendly'),
        'neutral': match.get('neutral', False)
    }


def deduplicate_matches(matches: List[Dict]) -> List[Dict]:
    """Remove duplicate match records.

    Two records are duplicates if same teams, date, and similar scores.
    """
    seen: Set[Tuple] = set()
    unique = []

    for match in matches:
        key = (
            match.get('home_team'),
            match.get('away_team'),
            str(match.get('date', ''))
        )
        if key not in seen:
            seen.add(key)
            unique.append(match)

    return unique
