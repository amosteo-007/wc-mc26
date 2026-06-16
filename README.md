# World Cup Outcome + Narrative Simulation Platform

A constrained forecasting console that couples a **Monte Carlo** simulator for 2026 World
Cup outcomes with an **OASIS/MiroFish-style** multi-agent narrative simulator for
off-pitch stakeholder reactions. Users make bounded selections; the platform computes
conditional tournament outcomes and then simulates the social world around them.

**Start with [`PLAN.md`](PLAN.md).** It links the five phase docs in `docs/`.

> ⚠️ Narrative output is a **scenario simulation, not a prediction**. The agent-crowd
> approach is unbenchmarked and polarizes faster than real populations. Outcome
> probabilities (Monte Carlo) and narrative reactions are different kinds of claim and
> are labeled differently throughout the product.

## Repo map
```
PLAN.md                      Master build plan (read first)
docs/                        Phase docs 01–05
  01-data-collection.md      What data, from where, in what shape
  02-data-pipeline.md        ingest → transform → validate → load
  03-components.md           The four backend services
  04-frontend-design.md      Six-step wizard + results console
  05-integration.md          End-to-end run, guardrails, deploy
data/schema/                 Postgres schema + Neo4j graph model
pipeline/                    ETL (ingest/transform/validate/load)
packs/                       Authored narrative context packs (JSON)
services/
  outcome-engine/            Python/FastAPI Monte Carlo (no LLM)
  orchestrator/              GPT conductor (premium model; plan/spec/QC/synthesis only)
  narrative-worker/          Cheap-model graph/persona/round sim (OASIS/MiroFish)
web/                         Next.js wizard console
docker-compose.yml           Local datastores + backend services
.env.example                 Copy to .env and fill in
```

## Architecture (request flow)
```
web → orchestrator → outcome-engine          (Monte Carlo)
                  → narrative-worker → Neo4j  (graph + agents + rounds)
                  → Postgres (run state, results)   Redis (job queue)
```
GPT is the conductor, not the orchestra: it plans, writes the world spec, runs QC, and
synthesizes — the cheap worker does all per-agent generation. That split is the core
cost-control requirement.

## Quick start

The full stack runs from `docker-compose.yml`. **No API keys are required** to run
end-to-end — without `PREMIUM_API_KEY`/`CHEAP_API_KEY` the orchestrator's premium
touchpoints fall back to deterministic templates and the narrative worker uses a
template post generator. Adding keys (in `.env`) upgrades those steps to live LLM calls.

```bash
cp .env.example .env          # optional: fill in model keys to enable live LLM calls

# 1. Bring up everything (datastores + the three backend services)
docker compose up -d --build

# 2. Frontend
cd web && npm install && npm run dev      # http://localhost:3000
```

Postgres seeds itself on first boot: `data/schema/schema.sql` then the three
`data/seed_*.sql` files are mounted into the init dir, so teams, blended Elo ratings,
and the 2026 format land automatically (no manual `psql` load). To re-seed after a
schema change, recreate the volume: `docker compose down -v && docker compose up -d`.

Service ports: orchestrator `:8000` (the only public API), outcome-engine `:8001`,
narrative-worker `:8002`, Postgres `:5432`, Neo4j `:7474/:7687`, Redis `:6379`.

### Try it without the UI
```bash
# Unconditional champion probabilities (Monte Carlo only)
curl -s localhost:8001/simulate -H 'content-type: application/json' \
  -d '{"n_runs":5000,"seed":1}' | jq '.champion_probs'

# Full combined run through the orchestrator (outcome + narrative + comparative top-3)
RID=$(curl -s localhost:8000/simulations -H 'content-type: application/json' -d '{
  "mode":"combined","condition":null,
  "narrative_packs":["fan","sponsor","media"],
  "audience_scope":["domestic_winner","rival","neutral"],
  "report_tier":"analyst"}' | jq -r .run_id)
curl -s localhost:8000/simulations/$RID | jq '{status, data_version, comparative: [.comparative[]._winner]}'
```

### Graph backend (Neo4j optional)
The narrative worker prefers Neo4j but falls back to an in-memory graph
(`services/narrative-worker/memory_graph.py`) when `NEO4J_URI` is unreachable, so the
narrative pipeline runs in dev/CI without Neo4j. Graph stats are approximate in that mode.

### Tests
```bash
cd services/outcome-engine   && python -m pytest tests/ -q   # run on the host (needs data/ seeds)
cd services/narrative-worker && python -m pytest tests/ -q   # run in-container (deps live there)
```

## Status
**M1–M4 implemented and verified end-to-end.** The outcome engine runs vectorized
Monte Carlo with FIFA-correct group ranking, best-thirds selection, the seeded R32
bracket, and **rejection-sampling conditions** (champion/finalist/path probabilities
plus `effective_runs`). The orchestrator drives the async job state machine, builds the
world spec, runs **comparative top-3** winner worlds at analyst/executive tier, and does
QC + synthesis. The narrative worker produces world-spec-aware sentiment, narrative
clusters, a sponsor matrix, media tone, and `[SYNTHETIC]`-tagged sample posts. Every
run is stamped with `data_version` for reproducibility. See `PLAN.md` for milestone
detail and `docs/05` "What's next" for deferred scope.

## Verified facts (June 2026)
- 2026 format: 48 teams, 12 groups of 4, top 2 + 8 best thirds → R32 → final; 104 matches. (FIFA)
- MiroFish: multi-agent sim engine on CAMEL-AI's OASIS framework; graph → personas →
  rounds → report; OpenAI-compatible backends.
