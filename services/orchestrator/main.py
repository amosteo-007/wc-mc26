"""Orchestrator — GPT conductor. The only public API."""
import os
import json
import logging
from typing import Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx

from models import (
    SimulationRequest, SimulationResponse, SimulationStatus,
    MatchRequest, MatchResponse,
    JobStatus, TIER_BUDGET
)
import database as db
from planner import plan_simulation
from world_spec import build_world_spec
from qc import run_qc
from synthesizer import synthesize
from rate_limiter import check_rate_limit, check_concurrent_sims

ALLOWED_ORIGINS = os.getenv(
    'ALLOWED_ORIGINS',
    'http://localhost:3000,http://127.0.0.1:3000'
).split(',')

app = FastAPI(title="WC2026 Orchestrator", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in ALLOWED_ORIGINS],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
    allow_credentials=True,
)

OUTCOME_ENGINE_URL = os.getenv(
    'OUTCOME_ENGINE_URL', 'http://localhost:8001'
)
NARRATIVE_WORKER_URL = os.getenv(
    'NARRATIVE_WORKER_URL', 'http://localhost:8002'
)
USE_LLM = bool(os.getenv('PREMIUM_API_KEY'))
# MC_ONLY=true strips narrative/combined from the public API — used on the
# Render free-tier deployment where only the outcome engine is running.
MC_ONLY = os.getenv('MC_ONLY', '').lower() in ('1', 'true', 'yes')
# Shared secret guarding POST /admin/refresh (results ingest). Unset = the admin
# endpoint is disabled (returns 503) so it can never be hit unauthenticated.
ADMIN_TOKEN = os.getenv('ADMIN_TOKEN')

_log = logging.getLogger("orchestrator.main")


def _client_ip(request: Request) -> str:
    """Extract client IP, respecting X-Forwarded-For."""
    forwarded = request.headers.get('X-Forwarded-For')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.client.host if request.client else '127.0.0.1'


PRESET_SCENARIOS = [
    {
        "id": "brazil_wins_combined",
        "label": "Brazil Wins — Full Combined",
        "description": "Brazil wins 2026 WC. Transfer rumors, value surges, and market reactions.",
        "mode": "combined",
        "condition": {"type": "team_wins", "params": {"team_fifa_code": "BRA"}},
        "narrative_packs": ["transfer_news"],
        "audience_scope": ["domestic_winner", "rival", "neutral", "sponsors"],
        "report_tier": "analyst"
    },
    {
        "id": "usa_hosts_outcome",
        "label": "USA Host Performance — Outcome Only",
        "description": "How far do the USA go as hosts? Outcome only.",
        "mode": "outcome",
        "condition": None,
        "narrative_packs": [],
        "audience_scope": ["domestic_winner"],
        "report_tier": "quick"
    },
    {
        "id": "underdog_semifinal",
        "label": "Underdog Semifinal — Full Narrative",
        "description": "An underdog reaches the semifinal. Transfer buzz around breakout stars.",
        "mode": "combined",
        "condition": {"type": "underdog_semifinal", "params": {}},
        "narrative_packs": ["transfer_news"],
        "audience_scope": ["domestic_winner", "rival", "neutral", "sponsors"],
        "report_tier": "analyst"
    },
    {
        "id": "argentina_exits_early",
        "label": "Argentina Group Exit Shock",
        "description": "Defending champions crash out in groups. Market panic and fire-sale rumors.",
        "mode": "combined",
        "condition": {"type": "team_exits_group", "params": {"team_fifa_code": "ARG"}},
        "narrative_packs": ["transfer_news"],
        "audience_scope": ["domestic_winner", "rival", "neutral", "regional_latam"],
        "report_tier": "executive"
    },
    {
        "id": "england_final_penalty",
        "label": "England Penalty Final",
        "description": "Final decided by penalties. Transfer value implications for England stars.",
        "mode": "combined",
        "condition": {"type": "penalty_final", "params": {}},
        "narrative_packs": ["transfer_news"],
        "audience_scope": ["domestic_winner", "rival", "neutral", "regional_eur"],
        "report_tier": "analyst"
    }
]


@app.get("/health")
async def health():
    return {"status": "ok", "service": "orchestrator"}


@app.get("/scenarios")
async def list_scenarios():
    scenarios = (
        [s for s in PRESET_SCENARIOS if s["mode"] == "outcome"]
        if MC_ONLY else PRESET_SCENARIOS
    )
    return {"scenarios": scenarios}


@app.get("/teams")
async def list_teams():
    """The actual tournament field — the wizard dropdown reads from this so it
    can never drift from the teams that are simulated."""
    return {"teams": db.get_teams()}


@app.get("/tournament")
async def tournament_state():
    """Official groups + live standings + auto-advancing knockout bracket.
    Renders the tournament view in the wizard."""
    try:
        return db.get_tournament_state()
    except Exception as e:
        _log.exception("tournament_state failed")
        raise HTTPException(status_code=500, detail="Failed to load tournament state")


class RefreshPayload(BaseModel):
    """Optional body for POST /admin/refresh — a results feed in our shape.

    Omit the body to pull from the configured feed (WC_RESULTS_SOURCE / URL).
    Provide it to enter/correct scores by hand.
    """
    edition: str = "WC2026"
    matches: list = []


@app.post("/admin/refresh")
async def admin_refresh(
    payload: Optional[RefreshPayload] = None,
    x_admin_token: Optional[str] = Header(default=None),
):
    """Ingest live results into wc_results, then standings + bracket re-derive.

    Auth: send the shared secret in the `X-Admin-Token` header. If ADMIN_TOKEN
    is unset on the server the endpoint is disabled (503). With no JSON body it
    pulls from the configured feed; with a body it upserts those matches.
    """
    if not ADMIN_TOKEN:
        raise HTTPException(status_code=503, detail="Admin refresh is not enabled.")
    if x_admin_token != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid admin token.")
    try:
        import results_refresh
        body = payload.model_dump() if payload and payload.matches else None
        summary = results_refresh.refresh(body)
        return {"status": "ok", **summary}
    except RuntimeError as e:
        # Configuration problem (no source) — safe to surface the message.
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        _log.exception("admin refresh failed")
        raise HTTPException(status_code=502, detail="Results refresh failed.")


@app.get("/packs")
async def list_packs():
    packs = [
        {"pack_type": "team", "entity_key": "BRA", "version": 1,
         "description": "Brazil — 5-time champions, samba legacy"},
        {"pack_type": "team", "entity_key": "ARG", "version": 1,
         "description": "Argentina — defending champions, Messi era"},
        {"pack_type": "team", "entity_key": "USA", "version": 1,
         "description": "USA — hosts, growing soccer nation"},
        {"pack_type": "team", "entity_key": "ENG", "version": 1,
         "description": "England — it's coming home, media pressure"},
        {"pack_type": "team", "entity_key": "FRA", "version": 1,
         "description": "France — Mbappé, deep talent pool"},
        {"pack_type": "sponsor", "entity_key": "fifa_partners", "version": 1,
         "description": "FIFA partner brand archetypes"},
        {"pack_type": "fan", "entity_key": "archetypes", "version": 1,
         "description": "Fan archetypes: ultra, casual, rival, neutral"},
        {"pack_type": "media", "entity_key": "broadcaster", "version": 1,
         "description": "Media/broadcaster lenses by region"},
    ]
    return {"packs": packs}


@app.post("/matches", response_model=MatchResponse)
async def simulate_match(req: MatchRequest, request: Request):
    """Single-match Monte Carlo. Synchronous — returns breakdown directly."""
    client_ip = _client_ip(request)

    if not check_rate_limit(client_ip, 'matches'):
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Please wait before requesting another match simulation.")

    try:
        # Validate codes differ
        if req.home_fifa_code.upper() == req.away_fifa_code.upper():
            raise HTTPException(status_code=422, detail="Home and away teams must differ")

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{OUTCOME_ENGINE_URL}/simulate/match",
                json=req.model_dump()
            )
            if resp.status_code == 404:
                raise HTTPException(status_code=404, detail=resp.json().get('detail', 'Team not found'))
            if resp.status_code == 422:
                raise HTTPException(status_code=422, detail=resp.json().get('detail', 'Invalid request'))
            resp.raise_for_status()
            return resp.json()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Match simulation failed")


@app.post("/simulations", response_model=SimulationResponse)
async def create_simulation(
    req: SimulationRequest, background_tasks: BackgroundTasks, request: Request
):
    """Create a new simulation. Enqueues background processing."""
    if MC_ONLY and req.mode.value != "outcome":
        raise HTTPException(
            status_code=422,
            detail="Only outcome simulations are available on this deployment (MC_ONLY=true)."
        )

    client_ip = _client_ip(request)

    # Rate limit check
    if not check_rate_limit(client_ip, 'simulations'):
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Please wait before creating another simulation.")

    # Concurrent cap
    if not check_concurrent_sims():
        raise HTTPException(status_code=429, detail="Too many simulations running. Please wait for one to complete.")

    try:
        # Clamp n_runs to executive ceiling
        n_runs = TIER_BUDGET[req.report_tier.value]['n_runs']
        max_runs = TIER_BUDGET['executive']['n_runs']
        n_runs = min(n_runs, max_runs)

        run_id = db.create_run(
            mode=req.mode.value,
            condition=req.condition,
            packs=req.narrative_packs,
            audience=req.audience_scope,
            tier=req.report_tier.value,
            n_runs=n_runs
        )
        background_tasks.add_task(process_simulation, run_id, req)
        return SimulationResponse(run_id=run_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/simulations/{run_id}", response_model=SimulationStatus)
async def get_simulation(run_id: str):
    """Poll simulation status. Returns partial results as available."""
    run = db.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    job = db.get_job_status(run_id)
    status = job.get('status', 'unknown')

    valid_statuses = [s.value for s in JobStatus]
    if status not in valid_statuses:
        status = 'failed'

    run_condition = run.get('condition')
    if isinstance(run_condition, str):
        try:
            run_condition = json.loads(run_condition)
        except (ValueError, TypeError):
            run_condition = None

    response = SimulationStatus(
        run_id=run_id,
        status=JobStatus(status),
        data_version=run.get('data_version'),
        mode=run.get('mode'),
        condition=run_condition
    )

    if status in ('outcome_done', 'narrative_running', 'synthesizing', 'done'):
        outcome_data = job.get('outcome')
        if outcome_data:
            response.outcome = json.loads(outcome_data)

    if status in ('synthesizing', 'done'):
        narrative_data = job.get('narrative')
        if narrative_data:
            response.narrative = json.loads(narrative_data)
        comparative_data = job.get('comparative')
        if comparative_data:
            response.comparative = json.loads(comparative_data)
        qc_data = job.get('qc_report')
        if qc_data:
            response.confidence = json.loads(qc_data)

    return response


async def process_simulation(run_id: str, req: SimulationRequest):
    """Background job: full simulation pipeline.

    For combined mode at analyst/executive tier, runs the narrative worker
    for the top-3 most likely champions and returns comparative results.
    """
    try:
        budget = TIER_BUDGET[req.report_tier.value]

        # Step 1: Run outcome engine
        db.update_run_status(run_id, 'outcome_running')

        # Narrative-only anchors on a user-picked subject team (modeled as a
        # team_wins condition) but does not display outcome probabilities, so we
        # skip the (potentially thin/slow) rejection sampling and run the engine
        # unconditionally just to populate the field — the narrative winner is
        # forced to the picked team below.
        engine_condition = None if req.mode.value == 'narrative' else req.condition

        async with httpx.AsyncClient(timeout=300.0) as client:
            outcome_resp = await client.post(
                f"{OUTCOME_ENGINE_URL}/simulate",
                json={
                    'n_runs': budget['n_runs'],
                    'condition': engine_condition,
                    'seed': hash(run_id) % (2**31)
                }
            )
            outcome_resp.raise_for_status()
            outcome = outcome_resp.json()

        r = db.get_redis()
        r.hset(f"job:{run_id}", mapping={
            'status': 'outcome_done',
            'outcome': json.dumps(outcome)
        })
        db.update_run_status(run_id, 'outcome_done')

        # If outcome-only, we're done
        if req.mode.value == 'outcome':
            r.hset(f"job:{run_id}", 'status', 'done')
            db.update_run_status(run_id, 'done')
            return

        # ---- Narrative path ----
        run_plan = {
            'edition': req.edition,
            'mode': req.mode.value,
            'condition': req.condition,
            'narrative_packs': req.narrative_packs,
            'audience_scope': req.audience_scope,
            'report_tier': req.report_tier.value,
            'budget': budget
        }

        # Determine how many winner-worlds to simulate.
        champion_probs = outcome.get('champion_probs', {})
        top_champions = sorted(
            champion_probs.items(), key=lambda x: x[1], reverse=True
        )
        # A `team_wins` condition pins that team as champion in 100% of kept
        # rollouts, so the engine drops it from champion_probs (it's a tautology
        # on the board). But the narrative must still anchor on that winner —
        # prepend it explicitly, otherwise there are no winner-worlds to simulate.
        cond = req.condition or {}
        if cond.get('type') == 'team_wins':
            pinned = (cond.get('params') or {}).get('team_fifa_code')
            if pinned:
                top_champions = (
                    [(pinned, 1.0)]
                    + [(t, p) for t, p in top_champions if t != pinned]
                )

        n_worlds = 1
        if req.report_tier.value in ('analyst', 'executive'):
            n_worlds = min(3, len(top_champions))

        db.update_run_status(run_id, 'narrative_running')
        r.hset(f"job:{run_id}", 'status', 'narrative_running')

        narratives = []
        async with httpx.AsyncClient(timeout=600.0) as client:
            for i, (winner_team, winner_prob) in enumerate(top_champions[:n_worlds]):
                # Build a world spec anchored on this specific winner
                winner_outcome = {
                    **outcome,
                    'selected_winner': winner_team,
                    'selected_winner_prob': winner_prob,
                }
                world_spec = build_world_spec(
                    winner_outcome, run_plan, use_llm=USE_LLM
                )
                world_spec['winner_team'] = winner_team
                world_spec['winner_probability'] = winner_prob

                try:
                    narrative_resp = await client.post(
                        f"{NARRATIVE_WORKER_URL}/run",
                        json={
                            'world_spec': world_spec,
                            'tier': req.report_tier.value,
                            'packs': req.narrative_packs,
                            'max_agents': budget['n_agents'],
                            'max_rounds': budget['n_rounds'],
                        }
                    )
                    if narrative_resp.status_code == 200:
                        nar = narrative_resp.json()
                        nar['_winner'] = winner_team
                        nar['_winner_prob'] = winner_prob
                        narratives.append(nar)
                except Exception:
                    narratives.append({
                        'narratives': [],
                        'sentiment': {},
                        'error': f'Worker call failed for {winner_team}',
                        '_winner': winner_team,
                        '_winner_prob': winner_prob
                    })

        primary_narrative = narratives[0] if narratives else {
            'narratives': [], 'sentiment': {}, 'error': 'No narratives produced'
        }

        # Step 4: QC + Synthesize (on primary narrative)
        db.update_run_status(run_id, 'synthesizing')
        r.hset(f"job:{run_id}", 'status', 'synthesizing')

        # Build world spec for primary for QC context
        primary_world = build_world_spec(outcome, run_plan, use_llm=USE_LLM)
        qc_report = run_qc(
            primary_narrative, primary_world, outcome, use_llm=USE_LLM
        )
        final_report = synthesize(
            outcome, primary_narrative, qc_report,
            req.report_tier.value, use_llm=USE_LLM
        )

        r.hset(f"job:{run_id}", mapping={
            'status': 'done',
            'narrative': json.dumps(primary_narrative),
            'comparative': json.dumps(narratives[1:] if len(narratives) > 1 else []),
            'qc_report': json.dumps(qc_report),
            'final_report': json.dumps(final_report)
        })
        db.update_run_status(run_id, 'done')

    except Exception as e:
        r = db.get_redis()
        r.hset(f"job:{run_id}", mapping={
            'status': 'failed',
            'error': str(e)
        })
        db.update_run_status(run_id, 'failed')
