"""Unit + slice tests for the outcome engine.

These run without a database: teams/ratings/format are loaded from the repo's
seed SQL files so the test exercises the real 12-group bracket. Run with:

    cd services/outcome-engine && python -m pytest tests/ -q
"""
import json
import re
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from models.bracket import rank_group, best_thirds, resolve_bracket, run_knockout
from models.simulator import simulate_one_tournament, run_simulation
from conditions.filters import build_condition_predicate

def _find_data_dir() -> Path:
    """Locate the repo's data/ dir from host or container layout."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "data" / "seed_format.sql"
        if candidate.exists():
            return parent / "data"
    # Not found anywhere up the tree; return a path that simply won't exist
    # so the module-level guard + skipif handle it gracefully.
    return here.parent / "data"


DATA = _find_data_dir()

pytestmark = pytest.mark.skipif(
    not (DATA / "seed_format.sql").exists(),
    reason="seed SQL not reachable (run from repo host, not the service container)",
)


def _load_format():
    text = (DATA / "seed_format.sql").read_text(encoding="utf-8")
    blob = text[text.index("'{"): text.rindex("}'") + 1].strip("'")
    return json.loads(blob)


def _load_teams():
    text = (DATA / "seed_teams.sql").read_text(encoding="utf-8")
    codes = re.findall(r"\('([A-Z]{3})',\s*'", text)
    return [{"id": i + 1, "fifa_code": c} for i, c in enumerate(codes)]


def _load_ratings(teams):
    text = (DATA / "seed_ratings.sql").read_text(encoding="utf-8")
    pairs = dict(re.findall(r"\('([A-Z]{3})',\s*(\d+)\)", text))
    by_code = {t["fifa_code"]: t["id"] for t in teams}
    return [
        {"team_id": by_code[c], "rating": float(r)}
        for c, r in pairs.items() if c in by_code
    ]


if (DATA / "seed_format.sql").exists():
    FORMAT = _load_format()
    TEAMS = _load_teams()
    RATINGS = _load_ratings(TEAMS)
else:  # collected-but-skipped when seeds aren't reachable (e.g. in container)
    FORMAT, TEAMS, RATINGS = {}, [], []


def test_rank_group_orders_by_points_then_gd_then_gf():
    teams = ["A", "B", "C", "D"]
    # A beats everyone; B,C,D ordered by GD/GF below.
    results = {
        ("A", "B"): (2, 0), ("A", "C"): (3, 0), ("A", "D"): (1, 0),
        ("B", "C"): (2, 1), ("B", "D"): (0, 0), ("C", "D"): (1, 1),
    }
    standings = rank_group(teams, results)
    assert standings[0]["team"] == "A"
    assert [s["rank"] for s in standings] == [1, 2, 3, 4]
    # Points are monotonically non-increasing down the table.
    pts = [s["pts"] for s in standings]
    assert pts == sorted(pts, reverse=True)


def test_best_thirds_returns_eight_sorted():
    rng = np.random.default_rng(0)
    standings = []
    for _ in range(12):
        s = [
            {"team": f"t{rng.integers(1000)}", "pts": int(rng.integers(0, 10)),
             "gd": int(rng.integers(-5, 5)), "gf": int(rng.integers(0, 8))}
            for _ in range(4)
        ]
        standings.append(s)
    thirds = best_thirds(standings)
    assert len(thirds) == 8
    keys = [(-t["pts"], -t["gd"], -t["gf"]) for t in thirds]
    assert keys == sorted(keys)


def test_resolve_bracket_yields_32_distinct_teams():
    groups = {g["group"]: g["teams"] for g in FORMAT["groups"]}
    elos = {t["fifa_code"]: 1900.0 for t in TEAMS}
    # Spread elos so groups have deterministic-ish winners.
    for i, t in enumerate(TEAMS):
        elos[t["fifa_code"]] = 2100.0 - i * 5
    rng = np.random.default_rng(1)
    rollout = simulate_one_tournament(groups, FORMAT["knockout_bracket"], elos, rng)
    # 32 advance, 16 (of 48) exit at group stage.
    assert len(rollout["group_exits"]) == 48 - 32
    assert rollout["champion"] in elos
    assert len(rollout["finalists"]) == 2
    assert rollout["champion"] in rollout["finalists"]
    assert len(rollout["semifinalists"]) == 4


def test_furthest_stage_is_consistent_for_champion():
    groups = {g["group"]: g["teams"] for g in FORMAT["groups"]}
    elos = {t["fifa_code"]: 1900.0 + (i % 10) for i, t in enumerate(TEAMS)}
    rng = np.random.default_rng(2)
    r = simulate_one_tournament(groups, FORMAT["knockout_bracket"], elos, rng)
    assert r["furthest"][r["champion"]] == "champion"
    for f in r["finalists"]:
        assert r["furthest"][f] in ("final", "champion")


def test_team_wins_predicate_filters_to_that_champion():
    pred = build_condition_predicate(
        {"type": "team_wins", "params": {"team_fifa_code": "BRA"}}, {}
    )
    assert pred({"champion": "BRA", "finalists": [], "semifinalists": [],
                 "furthest": {}, "group_exits": set()})
    assert not pred({"champion": "ARG", "finalists": [], "semifinalists": [],
                     "furthest": {}, "group_exits": set()})


def test_run_simulation_unconditional_probs_sum_to_one():
    out = run_simulation(TEAMS, RATINGS, FORMAT, n_runs=200, seed=42)
    total = sum(out["champion_probs"].values())
    assert out["effective_runs"] == 200
    assert abs(total - 1.0) < 1e-9
    assert out["confidence"]["acceptance_rate"] == 1.0
    assert len(out["top_paths"]) > 0


def test_run_simulation_conditional_reduces_effective_runs_and_drops_pinned_champion():
    cond = {"type": "team_wins", "params": {"team_fifa_code": "ARG"}}
    out = run_simulation(TEAMS, RATINGS, FORMAT, n_runs=400, condition=cond, seed=7)
    # ARG is the top-rated team; should win some but not all rollouts.
    assert 0 < out["effective_runs"] < 400
    # Conditional on ARG winning, ARG is champion in 100% of kept rollouts — a
    # tautology that carries no information, so the board drops it and shows only
    # the runner-up redistribution.
    assert "ARG" not in out["champion_probs"]
    assert out["confidence"]["thin_sample"] == (out["effective_runs"] < 100)


def test_strength_favors_higher_elo_over_many_runs():
    cond = {"type": "team_wins", "params": {"team_fifa_code": "ARG"}}
    weak = {"type": "team_wins", "params": {"team_fifa_code": "NZL"}}
    strong = run_simulation(TEAMS, RATINGS, FORMAT, n_runs=300, condition=cond, seed=3)
    feeble = run_simulation(TEAMS, RATINGS, FORMAT, n_runs=300, condition=weak, seed=3)
    # The strongest team wins far more often than the weakest.
    assert strong["effective_runs"] > feeble["effective_runs"]
