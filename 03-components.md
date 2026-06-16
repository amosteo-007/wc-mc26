# Phase 3 — Building Out Components

The four backend services. Build each as a **vertical slice** — a thin end-to-end path
first, then breadth. The directory stubs already exist under `services/`.

## Service 1 — Outcome Engine (`services/outcome-engine/`)
Deterministic-ish Monte Carlo. No LLM. The numeric heart of the product.

**Build order:**
1. `models/strength.py` — calibrate Elo→expectancy and the (bivariate) Poisson goal
   model against held-out historical tournaments. Replace placeholder coefficients.
2. `models/bracket.py` — implement `rank_group` (FIFA tiebreakers), `best_thirds`
   (8 best third-placed across 12 groups), and `run_knockout` (R32→final, ET/penalty).
3. `conditions/filters.py` — rejection sampling: simulate full tournaments, keep
   rollouts matching the condition, renormalize, track `effective_runs`.
4. `main.py` `/simulate` — load format + strengths → simulate N → filter → aggregate
   champion/finalist probs, top paths, upset frequencies, confidence.

**Performance:** vectorize with NumPy; target 100k tournaments in seconds, not minutes.
Rare conditions shrink `effective_runs` — return it so the UI can warn on thin samples.

**Slice-1 demo:** unconditional 2026 champion probabilities from seeded ratings.

## Service 2 — Orchestrator (`services/orchestrator/`)
The GPT conductor and the only public API. Premium model touches **four** things only:
plan, world spec, QC, final synthesis.

**Build order:**
1. `main.py` — `/simulations` (validate selections → enqueue → run_id),
   `/simulations/{id}` (poll), `/scenarios` (preset catalog).
2. `planner.py` — selections → outcome `Condition` + packs/archetypes + budget
   (`TIER_BUDGET`). Keep the premium prompt small and schema-constrained.
3. `world_spec.py` — after outcome is known, write the structured control file.
4. `qc.py` — validate worker output vs tracked metrics; flag low-confidence; synthesize.

**Cost rule (non-negotiable):** no premium-model call inside the per-agent or per-round
loop. If you find one there, move it to the worker.

**Slice-1 demo:** `outcome`-only run returns champion redistribution with no narrative.

## Service 3 — Narrative Worker (`services/narrative-worker/`)
Cheap model + OASIS/MiroFish runtime. Does all the high-volume work.

**Build order (mirrors MiroFish stages 4–7):**
1. `graph_builder.py` — world spec + packs → entities/relations/topics in Neo4j
   (seed extraction → GraphRAG). See `data/schema/graph_model.md`.
2. `persona.py` — instantiate crowd variants from archetypes; differentiate on
   influence, memory, network position, response speed. Never clone identical agents.
3. `simulation.py` — multi-round loop (post/reply/amplify/ignore/shift); persist
   per-round state; emit deltas. **Default ~12–40 rounds by tier** (token burn scales
   with agents × rounds — budget it).
4. `report.py` — structured intermediate: dominant narratives, sentiment curves,
   influential actors, sponsor pressure, media tone, turning points, sample posts.

**Validity guardrail in code:** tag every generated post as synthetic; record that the
crowd model is unbenchmarked and polarization-biased so QC can caveat the report.

**Slice-1 demo:** one pack (`fan_sentiment`) on a fixed "Spain wins" world → sentiment
curve + top narrative clusters.

## Service 4 — Frontend BFF / API surface
For v1 the orchestrator *is* the API. If the frontend needs aggregation/auth shaping
later, add a thin gateway then — don't pre-build it.

## API contract (orchestrator)
```
POST /simulations      {edition, mode, condition?, narrative_packs[], audience_scope[], report_tier} -> {run_id}
GET  /simulations/{id} -> {status, outcome?, narrative?, comparative?, confidence}
GET  /scenarios        -> [preset templates]
GET  /packs            -> [available context packs]
```
Internal: `outcome-engine POST /simulate`, `narrative-worker POST /run`.

## Cross-cutting (wire in during, not after)
- Structured logs + error tracking from the first real endpoint.
- Job state in Redis; runs are async — never block an HTTP request on a 100k sim.
- Secrets via env only; commit `.env.example`, never `.env`.

## Deliverables for Phase 3
- Outcome engine passing calibration tests; orchestrator running an `outcome`-only job;
  narrative worker running one pack end-to-end; the four-endpoint contract live.
