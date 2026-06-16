"""Pydantic models for orchestrator API."""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
from enum import Enum


class JobStatus(str, Enum):
    QUEUED = "queued"
    OUTCOME_RUNNING = "outcome_running"
    OUTCOME_DONE = "outcome_done"
    NARRATIVE_RUNNING = "narrative_running"
    SYNTHESIZING = "synthesizing"
    DONE = "done"
    FAILED = "failed"


class SimulationMode(str, Enum):
    OUTCOME = "outcome"
    NARRATIVE = "narrative"
    COMBINED = "combined"


class ReportTier(str, Enum):
    QUICK = "quick"
    ANALYST = "analyst"
    EXECUTIVE = "executive"


# Known whitelists
KNOWN_CONDITION_TYPES = {
    'team_exits_group', 'team_reaches_r16', 'team_reaches_qf',
    'team_reaches_sf', 'team_reaches_final', 'team_wins',
    'host_underperforms', 'underdog_semifinal', 'penalty_final',
    'refereeing_controversy',
}

KNOWN_PACKS = {'transfer_news'}

KNOWN_AUDIENCE_SCOPES = {
    'domestic_winner', 'rival', 'neutral', 'sponsors',
    'host_media', 'regional_latam', 'regional_eur',
    'regional_apac', 'regional_mena',
}

KNOWN_TEAM_CODES = set()  # Populated from DB at startup or on first request


class SimulationRequest(BaseModel):
    edition: str = "WC2026"
    mode: SimulationMode = SimulationMode.COMBINED
    condition: Optional[Dict[str, Any]] = None
    narrative_packs: List[str] = Field(default_factory=list, max_length=8)
    audience_scope: List[str] = Field(default_factory=list, max_length=12)
    report_tier: ReportTier = ReportTier.QUICK

    @field_validator('narrative_packs')
    @classmethod
    def validate_packs(cls, v):
        for pack in v:
            if pack not in KNOWN_PACKS:
                raise ValueError(f"Unknown narrative pack: {pack}. Known: {sorted(KNOWN_PACKS)}")
        return v

    @field_validator('audience_scope')
    @classmethod
    def validate_audience(cls, v):
        for scope in v:
            if scope not in KNOWN_AUDIENCE_SCOPES:
                raise ValueError(f"Unknown audience scope: {scope}")
        return v

    @field_validator('condition')
    @classmethod
    def validate_condition(cls, v):
        if v is not None:
            ctype = v.get('type', '')
            if ctype not in KNOWN_CONDITION_TYPES:
                raise ValueError(f"Unknown condition type: {ctype}")
            params = v.get('params', {})
            if 'team_fifa_code' in params:
                code = params['team_fifa_code']
                # We don't validate against the full team list here (DB round-trip),
                # but we validate format: must be 3 uppercase letters
                if not (isinstance(code, str) and len(code) == 3 and code.isalpha()):
                    raise ValueError(f"Invalid FIFA code: {code}")
        return v


class SimulationResponse(BaseModel):
    run_id: str
    status: JobStatus = JobStatus.QUEUED


class MatchRequest(BaseModel):
    home_fifa_code: str
    away_fifa_code: str
    n_runs: int = Field(default=20000, ge=1000, le=200000)
    neutral: bool = True
    goal_line: Optional[float] = Field(default=None, ge=0, le=15)
    seed: Optional[int] = None


class MatchResponse(BaseModel):
    home_team: Dict[str, Any]
    away_team: Dict[str, Any]
    win_home: float
    draw: float
    win_away: float
    expected_goals_home: float
    expected_goals_away: float
    expected_total: float
    mean_simulated_home: float
    mean_simulated_away: float
    total_goals_distribution: Dict[str, float]
    over_under: Dict[str, float]
    both_teams_score: float
    top_scorelines: List[Dict[str, Any]]
    goal_line_query: Optional[Dict[str, Any]] = None
    confidence: Dict[str, Any]
    data_version: Optional[Dict[str, Any]] = None


class SimulationStatus(BaseModel):
    run_id: str
    status: JobStatus
    data_version: Optional[str] = None
    mode: Optional[str] = None
    condition: Optional[Dict[str, Any]] = None
    outcome: Optional[Dict[str, Any]] = None
    narrative: Optional[Dict[str, Any]] = None
    comparative: Optional[List[Dict[str, Any]]] = None
    confidence: Optional[Dict[str, Any]] = None
    disclaimer: str = (
        "Scenario simulation, not a prediction. "
        "Narrative reactions are unbenchmarked and crowds may over-polarize."
    )


class ScenarioTemplate(BaseModel):
    id: str
    label: str
    description: str
    mode: SimulationMode
    condition: Optional[Dict[str, Any]] = None
    narrative_packs: List[str] = Field(default_factory=list)
    audience_scope: List[str] = Field(default_factory=list)
    report_tier: ReportTier = ReportTier.QUICK


class PackInfo(BaseModel):
    pack_type: str
    entity_key: Optional[str]
    version: int
    description: str


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None


# Tier budgets
TIER_BUDGET = {
    'quick': {'n_runs': 10000, 'n_agents': 50, 'n_rounds': 12},
    'analyst': {'n_runs': 50000, 'n_agents': 200, 'n_rounds': 24},
    'executive': {'n_runs': 100000, 'n_agents': 500, 'n_rounds': 40},
}
