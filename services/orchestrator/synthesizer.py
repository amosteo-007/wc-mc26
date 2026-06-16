"""Combine outcome + narrative + QC into final report. Premium model optional."""
import os
import json
import logging
from typing import Dict, Optional

_log = logging.getLogger("orchestrator.synthesizer")


def synthesize(
    outcome: Dict,
    narrative: Optional[Dict],
    qc_report: Dict,
    tier: str,
    use_llm: bool = False
) -> Dict:
    """Build the final assembled report.

    Returns the complete payload for the frontend results console.
    """
    champion_probs = outcome.get('champion_probs', {})
    sorted_champions = sorted(
        champion_probs.items(), key=lambda x: x[1], reverse=True
    )

    report = {
        'outcome': {
            'champion_probs': dict(sorted_champions[:10]),
            'effective_runs': outcome.get('effective_runs', 0),
            'confidence': outcome.get('confidence', {}),
            'top_paths': outcome.get('top_paths', []),
            'upset_freq': outcome.get('upset_freq', {})
        },
        'narrative': narrative or {},
        'qc': qc_report,
        'comparative': None,
        'disclaimer': 'Scenario simulation, not a prediction.',
        'polarization_note': qc_report.get('polarization_caveat', '')
    }

    if use_llm and narrative:
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
                        f"You are synthesizing a {tier}-tier World Cup "
                        "simulation report. Write an executive summary "
                        "(200 words) covering the key outcome and narrative "
                        "findings. Return JSON: "
                        '{"executive_summary": "...", "key_takeaways": [...], '
                        '"risk_flags": [...]}'
                    )
                }, {
                    "role": "user",
                    "content": (
                        f"Outcome: {json.dumps(report['outcome'])}\n"
                        f"Narrative clusters: "
                        f"{json.dumps(narrative.get('narratives', {}))}"
                    )
                }],
                max_tokens=500,
                temperature=0.5,
            )
            report['synthesis'] = json.loads(content)
        except Exception as exc:
            _log.warning("synthesis LLM failed: %s", exc)
            report['synthesis'] = {
                'executive_summary': 'Synthesis unavailable.',
                'key_takeaways': [],
                'risk_flags': []
            }

    return report
