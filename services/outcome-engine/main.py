"""Outcome Engine — Monte Carlo tournament simulator. No LLM."""
import uuid
from typing import Optional
import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import database as db
from models.simulator import run_simulation, compute_form_adjustment
from models.match_sim import simulate_match
from conditions.filters import get_preset_conditions

app = FastAPI(title="Outcome Engine", version="0.1.0")


class MatchRequest(BaseModel):
    home_fifa_code: str
    away_fifa_code: str
    n_runs: int = Field(default=20000, ge=1000, le=200000)
    neutral: bool = True
    goal_line: Optional[float] = Field(default=None, ge=0, le=15)
    seed: Optional[int] = None


class MatchResponse(BaseModel):
    home_team: dict
    away_team: dict
    win_home: float
    draw: float
    win_away: float
    expected_goals_home: float
    expected_goals_away: float
    expected_total: float
    mean_simulated_home: float
    mean_simulated_away: float
    total_goals_distribution: dict
    over_under: dict
    both_teams_score: float
    top_scorelines: list
    goal_line_query: Optional[dict] = None
    confidence: dict
    data_version: Optional[dict] = None


class SimulationRequest(BaseModel):
    n_runs: int = 10000
    condition: Optional[dict] = None
    data_version: Optional[str] = None
    seed: Optional[int] = None


class SimulationResponse(BaseModel):
    run_id: str
    champion_probs: dict
    finalist_probs: dict
    stage_probs: dict
    top_paths: list
    effective_runs: int
    confidence: dict
    n_runs: int
    data_version: Optional[dict] = None


@app.get("/health")
async def health():
    return {"status": "ok", "service": "outcome-engine"}


@app.post("/simulate", response_model=SimulationResponse)
async def simulate(req: SimulationRequest):
    """Run Monte Carlo tournament simulation.

    Returns champion probabilities, effective runs (after filtering),
    and confidence flags.
    """
    try:
        teams = db.get_teams()
        if not teams:
            raise HTTPException(status_code=500, detail="No teams in database")

        ratings = db.get_ratings()
        format_spec = db.get_format()
        if not format_spec:
            raise HTTPException(status_code=500, detail="No tournament format found")

        # Fetch recent matches for form adjustments (±40 Elo max per team)
        team_codes = [t['fifa_code'] for t in teams]
        matches = db.get_recent_matches(team_codes)

        data_version = db.get_data_version()

        result = run_simulation(
            teams=teams,
            ratings=ratings,
            format_spec=format_spec,
            n_runs=req.n_runs,
            condition=req.condition,
            seed=req.seed,
            matches=matches,
        )

        run_id = str(uuid.uuid4())

        sorted_champ = sorted(
            result['champion_probs'].items(),
            key=lambda x: x[1], reverse=True
        )
        sorted_finalist = sorted(
            result['finalist_probs'].items(),
            key=lambda x: x[1], reverse=True
        )

        return SimulationResponse(
            run_id=run_id,
            champion_probs=dict(sorted_champ[:10]),
            finalist_probs=dict(sorted_finalist[:10]),
            stage_probs=result.get('stage_probs', {}),
            top_paths=result['top_paths'],
            effective_runs=result['effective_runs'],
            confidence=result['confidence'],
            n_runs=req.n_runs,
            data_version=data_version
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/conditions")
async def list_conditions():
    """Return available preset conditions."""
    return {"conditions": get_preset_conditions()}


@app.post("/simulate/match", response_model=MatchResponse)
async def simulate_match_endpoint(req: MatchRequest):
    """Run single-match Monte Carlo simulation.

    Returns win/draw/loss probabilities, goal distributions,
    over/under lines, both-teams-to-score, and top scorelines.
    """
    try:
        # Validate codes differ
        if req.home_fifa_code.upper() == req.away_fifa_code.upper():
            raise HTTPException(status_code=422, detail="Home and away teams must differ")

        # Look up both teams
        home_team = db.get_team_by_code(req.home_fifa_code.upper())
        away_team = db.get_team_by_code(req.away_fifa_code.upper())

        if not home_team:
            raise HTTPException(status_code=404, detail=f"Unknown team: {req.home_fifa_code}")
        if not away_team:
            raise HTTPException(status_code=404, detail=f"Unknown team: {req.away_fifa_code}")

        # Fetch ratings
        ratings = db.get_ratings()
        team_elos = {}
        rated = 0
        for t in [home_team, away_team]:
            team_ratings = [r['rating'] for r in ratings if r['team_id'] == t['id']]
            if team_ratings:
                team_elos[t['fifa_code']] = float(np.mean(team_ratings))
                rated += 1
            else:
                team_elos[t['fifa_code']] = 1800.0
        rating_coverage = rated / 2.0

        # Fetch form matches and compute adjustment
        codes = [home_team['fifa_code'], away_team['fifa_code']]
        matches = db.get_matches_for_teams(codes)
        form_adjustments = {}
        if matches:
            form_adjustments = compute_form_adjustment(codes, team_elos, matches)
        form_applied = any(abs(v) > 1e-9 for v in form_adjustments.values())

        home_elo = team_elos[home_team['fifa_code']] + form_adjustments.get(home_team['fifa_code'], 0)
        away_elo = team_elos[away_team['fifa_code']] + form_adjustments.get(away_team['fifa_code'], 0)

        # Determine host status
        is_host_home = home_team['fifa_code'] in ('USA', 'MEX', 'CAN') and not req.neutral

        result = simulate_match(
            home_elo=home_elo,
            away_elo=away_elo,
            n_runs=req.n_runs,
            neutral=req.neutral,
            is_host_home=is_host_home,
            goal_line=req.goal_line,
            seed=req.seed,
            form_applied=form_applied,
            rating_coverage=rating_coverage,
        )

        data_version = db.get_data_version()

        return MatchResponse(
            home_team={
                'fifa_code': home_team['fifa_code'],
                'name': home_team['name'],
                'confederation': home_team['confederation'],
                'elo': round(home_elo, 1),
            },
            away_team={
                'fifa_code': away_team['fifa_code'],
                'name': away_team['name'],
                'confederation': away_team['confederation'],
                'elo': round(away_elo, 1),
            },
            **result,
            data_version=data_version,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
