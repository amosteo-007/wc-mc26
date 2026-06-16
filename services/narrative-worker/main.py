"""Narrative Worker — OASIS/MiroFish multi-agent sim. CHEAP MODEL ONLY."""
import os
from fastapi import FastAPI, HTTPException
from models import RunRequest

import database as db
from graph_builder import build_full_graph
from persona import generate_personas, assign_network_positions
from simulation import run_full_simulation

app = FastAPI(title="Narrative Worker", version="0.1.0")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "narrative-worker"}


@app.post("/run")
async def run_narrative(req: RunRequest):
    """Run the full narrative simulation pipeline.

    1. Build knowledge graph
    2. Instantiate personas
    3. Run multi-round social simulation
    4. Return structured report
    """
    try:
        driver = db.get_driver()
        world_spec = req.world_spec
        packs = req.packs
        tier = req.tier

        # Initialize cheap model client if credentials available
        model_client = None
        if os.getenv('CHEAP_API_KEY'):
            try:
                import openai
                model_client = openai.OpenAI(
                    api_key=os.getenv('CHEAP_API_KEY'),
                    base_url=os.getenv('CHEAP_BASE_URL')
                )
            except Exception:
                pass

        # Step 1: Build graph
        graph_stats = build_full_graph(driver, world_spec, packs, model_client)

        # Step 2: Generate personas
        audience_scope = world_spec.get('audience_scope', ['neutral'])
        persona_ids = generate_personas(
            driver, audience_scope, tier, world_spec, model_client
        )

        # Step 3: Assign network positions
        network_stats = assign_network_positions(persona_ids)

        # Step 4: Run simulation
        result = run_full_simulation(driver, world_spec, tier, model_client)

        report = {
            'narratives': result.get('narratives', []),
            'sentiment': result.get('sentiment', {}),
            'sample_posts': result.get('sample_posts', []),
            'turning_points': result.get('turning_points', []),
            'world_context': result.get('world_context', {}),
            'confidence': {
                'graph_stats': graph_stats,
                'network_stats': network_stats,
                'total_posts': result.get('total_posts', 0),
                'rounds_completed': result.get('rounds_completed', 0)
            },
            'metadata': {
                'synthetic_label': True,
                'model_type': 'cheap' if model_client else 'template',
                'narrative_scope': 'transfer_news',
                'polarization_caveat': (
                    'LLM agent crowds over-polarize vs real populations. '
                    'This simulation is unbenchmarked. Narrative output is '
                    'a scenario, not a calibrated prediction.'
                )
            }
        }

        return report

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
