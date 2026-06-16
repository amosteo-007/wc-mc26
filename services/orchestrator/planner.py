"""Selections → run plan with tier budget. Premium model optional."""
import os
import json
import logging
from typing import Dict, List, Optional
from models import TIER_BUDGET

_log = logging.getLogger("orchestrator.planner")


def plan_simulation(
    edition: str,
    mode: str,
    condition: Optional[Dict],
    narrative_packs: List[str],
    audience_scope: List[str],
    report_tier: str,
    use_llm: bool = False
) -> Dict:
    """Convert user selections into a structured run plan.

    The LLM (when enabled) enriches the plan with contextual reasoning.
    Otherwise returns a deterministic mapping.
    """
    budget = TIER_BUDGET.get(report_tier, TIER_BUDGET['quick'])

    plan = {
        'edition': edition,
        'mode': mode,
        'condition': condition,
        'narrative_packs': narrative_packs,
        'audience_scope': audience_scope,
        'report_tier': report_tier,
        'budget': budget,
        'llm_enrichment': None
    }

    if use_llm and condition:
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
                        "You are a simulation planner. Given a condition and "
                        "narrative packs, suggest the most important narrative "
                        "dimensions to track. Return valid JSON only: "
                        '{"dimensions": [...], "focus_teams": [...], "key_themes": [...]}'
                    )
                }, {
                    "role": "user",
                    "content": (
                        f"Condition: {condition}\n"
                        f"Packs: {narrative_packs}\n"
                        f"Audience: {audience_scope}"
                    )
                }],
                max_tokens=300,
                temperature=0.3,
            )
            plan['llm_enrichment'] = json.loads(content)
        except Exception as exc:
            _log.warning("planner LLM enrichment failed: %s", exc)
            plan['llm_enrichment'] = None

    return plan
