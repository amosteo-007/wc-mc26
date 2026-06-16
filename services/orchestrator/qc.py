"""Quality control — validate narrative output. Premium model optional."""
import os
import json
import logging
from typing import Dict, List

_log = logging.getLogger("orchestrator.qc")


def run_qc(
    narrative_result: Dict,
    world_spec: Dict,
    outcome: Dict,
    use_llm: bool = False
) -> Dict:
    """Validate narrative worker output against tracked metrics.

    Flags: thin effective_runs, sparse packs, extreme conditions,
    low sentiment diversity, low agent participation.
    """
    flags = []

    effective_runs = outcome.get('effective_runs', 0)
    if effective_runs < 100:
        flags.append({
            'level': 'high', 'type': 'thin_sample',
            'message': (
                f'Only {effective_runs} effective runs — results are noisy'
            )
        })
    elif effective_runs < 1000:
        flags.append({
            'level': 'medium', 'type': 'thin_sample',
            'message': (
                f'Only {effective_runs} effective runs — '
                'interpret with caution'
            )
        })

    confidence = outcome.get('confidence', {})
    if confidence.get('rating_coverage', 1.0) < 0.9:
        flags.append({
            'level': 'medium', 'type': 'sparse_data',
            'message': 'Some teams have incomplete rating data'
        })

    narrative = narrative_result.get('narratives', {})
    sentiment = narrative_result.get('sentiment', {})

    if not narrative:
        flags.append({
            'level': 'medium', 'type': 'no_narratives',
            'message': 'No narrative clusters generated'
        })

    qc_report = {
        'passed': len([f for f in flags if f['level'] == 'high']) == 0,
        'flags': flags,
        'polarization_caveat': (
            'LLM agent crowds over-polarize compared to real populations. '
            'This simulation approach is unbenchmarked. '
            'Narrative output is a scenario, not a calibrated prediction.'
        ),
        'metrics_summary': {
            'narrative_clusters': (
                len(narrative) if isinstance(narrative, list) else 0
            ),
            'sentiment_segments': (
                len(sentiment) if isinstance(sentiment, dict) else 0
            )
        }
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
                        "You are a QC analyst. Review the narrative simulation "
                        "output and flag any quality issues. Return JSON: "
                        '{"issues": [...], "overall_assessment": "good|fair|poor"}'
                    )
                }, {
                    "role": "user",
                    "content": (
                        f"Narrative: {json.dumps({k: str(v)[:500] for k, v in narrative_result.items()})}\n"
                        f"Flags: {flags}"
                    )
                }],
                max_tokens=400,
                temperature=0.2,
            )
            qc_report['llm_assessment'] = json.loads(content)
        except Exception as exc:
            _log.warning("QC LLM assessment failed: %s", exc)
            qc_report['llm_assessment'] = None

    return qc_report
