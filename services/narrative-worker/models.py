"""Pydantic models for narrative worker."""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class RunRequest(BaseModel):
    world_spec: Dict[str, Any]
    tier: str = "quick"
    packs: List[str] = Field(default_factory=list)


class NarrativeCluster(BaseModel):
    cluster_id: str
    label: str
    dominance: float = 0.0
    agent_count: int = 0
    key_terms: List[str] = Field(default_factory=list)


class NarrativeReport(BaseModel):
    narratives: List[Dict[str, Any]] = Field(default_factory=list)
    sentiment: Dict[str, Any] = Field(default_factory=dict)
    sample_posts: List[Dict[str, Any]] = Field(default_factory=list)
    turning_points: List[Dict[str, Any]] = Field(default_factory=list)
    confidence: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=lambda: {
        'model_type': 'cheap',
        'synthetic_label': True,
        'polarization_caveat': (
            'LLM agent crowds over-polarize vs real populations. '
            'Unbenchmarked approach.'
        ),
        'graph_stats': {}
    })
