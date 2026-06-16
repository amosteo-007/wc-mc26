"""Build the structured control file for the narrative worker."""
import os
import json
import logging
from pathlib import Path
from typing import Dict, List

_log = logging.getLogger("orchestrator.world_spec")


def _packs_root() -> Path:
    """Locate the packs/ directory across host and container layouts.

    In Docker the orchestrator lives at /app, so a fixed parents[N] walk
    overflows (raising IndexError). Honor PACKS_DIR first, then try the
    container mount point and a couple of repo-relative candidates.
    """
    env = os.getenv('PACKS_DIR')
    candidates = []
    if env:
        candidates.append(Path(env))
    candidates.append(Path('/packs'))  # container mount
    here = Path(__file__).resolve()
    # Repo-relative candidates (host layout: services/orchestrator/world_spec.py)
    candidates.extend(p / 'packs' for p in here.parents)
    for c in candidates:
        if c.is_dir():
            return c
    return Path('/packs')


def _load_winner_stars(team_code: str) -> list:
    """Load the stars list from a team context pack.

    Falls back to a minimal default star list if the pack file
    doesn't exist or can't be parsed.
    """
    if not team_code:
        return _default_stars()

    pack_path = _packs_root() / 'team' / f'{team_code}.json'

    try:
        if pack_path.exists():
            data = json.loads(pack_path.read_text(encoding='utf-8'))
            stars = data.get('payload', {}).get('stars', [])
            if stars:
                return stars
    except (json.JSONDecodeError, KeyError, OSError, IndexError):
        pass

    return _default_stars()


def _default_stars() -> list:
    """Minimal fallback star list -- used when no team pack exists."""
    return [
        {'name': 'Key Forward', 'position': 'FW', 'age': 26, 'estimated_value_m': 80},
        {'name': 'Star Midfielder', 'position': 'MF', 'age': 24, 'estimated_value_m': 65},
        {'name': 'Veteran Defender', 'position': 'DF', 'age': 30, 'estimated_value_m': 30},
    ]


def build_world_spec(
    outcome: Dict, run_plan: Dict, use_llm: bool = False
) -> Dict:
    """After outcome is known, create the structured world spec.

    The world spec is the control file the narrative worker uses to:
    - Know which teams/stakeholders matter
    - Which narrative packs to activate
    - Which audience archetypes to instantiate
    - Temporal horizon and metrics to track
    """
    champion_probs = outcome.get('champion_probs', {})
    top_teams = sorted(
        champion_probs.items(), key=lambda x: x[1], reverse=True
    )[:5]

    spec = {
        'world_version': '1.0',
        'edition': run_plan.get('edition', 'WC2026'),
        'outcome_summary': {
            'top_champions': [
                {'team': t, 'probability': round(p, 4)}
                for t, p in top_teams
            ],
            'effective_runs': outcome.get('effective_runs', 0),
            'confidence': outcome.get('confidence', {})
        },
        'narrative_packs': run_plan.get('narrative_packs', []),
        'audience_scope': run_plan.get('audience_scope', []),
        'tier': run_plan.get('report_tier', 'quick'),
        'budget': run_plan.get('budget', {}),
        'temporal_horizon': ['24h', '72h', '7d'],
        'metrics': [
            'sentiment_by_audience', 'sponsor_pressure', 'media_tone',
            'narrative_diversity', 'influential_actors', 'turning_points'
        ],
        'llm_context': None
    }

    if use_llm:
        try:
            import openai
            from llm import chat_json
            client = openai.OpenAI(
                api_key=os.getenv('PREMIUM_API_KEY'),
                base_url=os.getenv('PREMIUM_BASE_URL')
            )
            content = chat_json(
                client,
                os.getenv('PREMIUM_MODEL', 'gpt-4o'),
                [{
                    "role": "system",
                    "content": (
                        "You are building a world-spec for a narrative simulation. "
                        "Given the outcome data, write a rich situational brief "
                        "(300 words max) describing the tournament outcome, key "
                        "moments, and narrative implications. This seeds the "
                        "simulation. Return JSON: "
                        '{"situational_brief": "...", "key_events": [...], '
                        '"stakeholders": [...]}'
                    )
                }, {
                    "role": "user",
                    "content": (
                        f"Outcome: {json.dumps(spec['outcome_summary'])}\n"
                        f"Packs: {spec['narrative_packs']}"
                    )
                }],
                max_tokens=600,
                temperature=0.7,
            )
            spec['llm_context'] = json.loads(content)
        except Exception as exc:
            _log.warning("world_spec LLM context failed: %s", exc)
            spec['llm_context'] = None

    # Load winner stars from team pack for transfer/news narrative
    winner_team = (outcome.get('selected_winner') or
                   (top_teams[0][0] if top_teams else None))
    spec['winner_stars'] = _load_winner_stars(winner_team)
    spec['winner_team'] = winner_team
    spec['winner_probability'] = dict(top_teams).get(winner_team, 0.0) if winner_team else 0.0
    spec['narrative_scope'] = 'transfer_news'

    return spec
