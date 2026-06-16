"""Smoke tests for the narrative worker against the in-memory graph backend.

No Neo4j and no LLM required — exercises the template/in-memory path that the
M3 milestone depends on. Run with:

    cd services/narrative-worker && python -m pytest tests/ -q
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from memory_graph import MemoryDriver
from graph_builder import build_full_graph
from persona import generate_personas, assign_network_positions
from simulation import (
    run_full_simulation, compile_narrative_clusters, detect_turning_points,
)

# The transfer/news narrative cast (mirrors persona.py archetypes).
ARCHETYPES = [
    "transfer_insider", "club_scout", "selling_club_fan", "buying_club_fan",
    "agent_source", "beat_reporter", "market_analyst", "rumor_aggregator",
    "casual_follower",
]


def _world_spec(winner="BRA", packs=("transfer_news",)):
    return {
        "winner_team": winner,
        "winner_probability": 0.12,
        "narrative_packs": list(packs),
        "audience_scope": ["domestic_winner", "rival", "neutral"],
        "edition": "WC2026",
        "narrative_scope": "transfer_news",
        "winner_stars": [
            {"name": "Vinícius Júnior", "position": "FW", "estimated_value_m": 150},
            {"name": "Endrick", "position": "FW", "estimated_value_m": 80},
        ],
    }


def test_memory_driver_runs_full_pipeline():
    driver = MemoryDriver()
    spec = _world_spec()
    build_full_graph(driver, spec, spec["narrative_packs"], model_client=None)
    persona_ids = generate_personas(
        driver, spec["audience_scope"], "quick", spec, model_client=None
    )
    assert len(persona_ids) > 0
    assign_network_positions(persona_ids)

    result = run_full_simulation(driver, spec, "quick", model_client=None)
    assert result["rounds_completed"] == 12  # quick tier
    assert len(result["sentiment"]["overall"]) == 12
    assert result["total_posts"] >= 0
    # Every sample post is tagged synthetic.
    for post in result["sample_posts"]:
        assert post["synthetic"] is True
        assert "[SYNTHETIC]" in post["content"]


def test_world_spec_shapes_narrative_clusters():
    # Posts carry their archetype (as generate_post sets it).
    posts = [
        {"agent_id": f"persona_transfer_insider_{i}_abc", "archetype": "transfer_insider"}
        for i in range(10)
    ]
    clusters = compile_narrative_clusters(None, posts, _world_spec(winner="BRA"))
    labels = [c["label"] for c in clusters]
    assert any("BRA" in l for l in labels)
    # Dominance is a normalized fraction.
    assert all(0.0 <= c["dominance"] <= 1.0 for c in clusters)


def test_clusters_spread_across_archetypes():
    """Regression: every archetype must route to its cluster, not collapse into
    one bucket. (Bug: clustering parsed the archetype out of the persona id with
    a naive split, so transfer_insider/club_scout/etc. all fell to the default.)"""
    posts = []
    for arch in ARCHETYPES:
        for _ in range(5):
            posts.append({"agent_id": f"persona_{arch}_0_abc", "archetype": arch})

    clusters = compile_narrative_clusters(None, posts, _world_spec(winner="BRA"))

    # All posts are accounted for.
    assert sum(c["agent_count"] for c in clusters) == len(posts)
    # The 9 archetypes map onto 5 distinct clusters — at least 4 must be non-empty
    # (a regression that collapsed everything would leave only one populated).
    populated = [c for c in clusters if c["agent_count"] > 0]
    assert len(populated) >= 4


def test_turning_points_detects_sharp_moves():
    flat = [0.1, 0.1, 0.1, 0.1]
    assert detect_turning_points(flat) == []
    spiky = [0.0, 0.0, 0.3, 0.3, -0.2]
    tps = detect_turning_points(spiky)
    assert len(tps) > 0
    assert all("direction" in t and "magnitude" in t for t in tps)
