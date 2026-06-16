# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

A constrained **forecasting console** for the 2026 FIFA World Cup (48 teams, 12 groups, 104 matches). Two subsystems: a **Monte Carlo outcome engine** (numeric) and an **OASIS/MiroFish-style multi-agent narrative simulator** (LLM-driven stakeholder reactions). Narrative output is **scenario simulation, not prediction** — the approach is unbenchmarked and LLM crowds polarize faster than real populations.

**Current status:** scaffold + phased plan. No business logic implemented yet. Build order follows `PLAN.md` milestones M1→M4.

## Architecture (the rule that shapes everything)

```
web (Next.js) → orchestrator (FastAPI, premium LLM) → outcome-engine (FastAPI, no LLM)
                                                     → narrative-worker (FastAPI, cheap LLM) → Neo4j
                                                     → Postgres + Redis
```

**The premium/cheap split is non-negotiable.** The GPT orchestrator touches only four things: plan, world spec, QC, and final synthesis. All per-agent and per-round generation runs on the cheap model in the narrative worker. If you find a premium-model call inside an agent/round loop, move it.

## Tech stack

| Layer | Choice | Purpose |
|---|---|---|
| Outcome engine | Python + FastAPI, NumPy/SciPy | Vectorized Monte Carlo (100k tournaments in seconds) |
| Orchestrator | Python + FastAPI, premium LLM | Conductor: plan, world spec, QC, synthesis |
| Narrative worker | Python + FastAPI, OASIS, cheap LLM | High-volume agent generation (graph → personas → rounds → report) |
| Structured store | PostgreSQL | Teams, ratings, results, run state |
| Narrative graph | Neo4j | Entities/relations/topics |
| Queue | Redis | Async job state (runs are long; UI polls) |
| Frontend | Next.js (App Router) + TS + Tailwind | Six-step wizard + results console |

## Milestones (build in this order)

- **M1** — Schema + seeded teams/ratings; outcome engine returns unconditional champion probabilities. _(Phase 1–3, outcome slice)_
- **M2** — Conditional outcomes via rejection sampling; UI Steps 1–3 + champion redistribution table. _(Phase 3–4)_
- **M3** — One narrative pack end-to-end on a fixed winner; sentiment + narrative clusters render. _(Phase 3–4)_
- **M4** — Full combined run; comparative top-3 mode; guardrail labeling + confidence flags. _(Phase 5)_

## Project structure (planned)

```
PLAN.md                        # Master build plan (read first)
docs/                          # Phase docs 01–05
data/schema/                   # Postgres schema + Neo4j graph model
pipeline/                      # ETL (ingest/transform/validate/load)
packs/                         # Authored narrative context packs (JSON)
services/
  outcome-engine/              # Python/FastAPI Monte Carlo (no LLM)
  orchestrator/                # GPT conductor (premium model; plan/spec/QC/synthesis only)
  narrative-worker/            # Cheap-model graph/persona/round sim (OASIS/MiroFish)
web/                           # Next.js wizard console
docker-compose.yml             # Local datastores + backend services
.env.example                   # Copy to .env and fill in
```

## Environment setup

```bash
cp .env.example .env          # fill in model keys + datastore creds
docker compose up -d postgres neo4j redis
psql "$POSTGRES_URL" -f data/schema/schema.sql

# backend services
docker compose up --build outcome-engine orchestrator narrative-worker

# frontend
cd web && npm install && npm run dev
```

This is a Windows 11 environment with PowerShell. The `set-ds-env.ps1` script sets DeepSeek API environment variables for the Claude Code harness itself (not for the project services).

## Key constraints

1. **Constrained UI, not a prompt box.** Every user input is dropdown, radio, or multi-select. The wizard maps selections to MC conditions and narrative packs — users never author simulations from scratch.
2. **Data versioning.** Pin `data_version` (snapshot date + pack versions) on every `sim_run` for reproducibility.
3. **Confidence flags.** Surfaced from data quality gates (coverage, freshness, cross-source consistency) through to the UI. Thin `effective_runs` from rare rejection-sampling conditions must warn the user.
4. **Synthetic labeling.** Every generated post tagged as synthetic. No fabricated quotes attributed to named real people in packs or output.
5. **Cost ceilings.** Tier caps (runs/agents/rounds) enforced server-side, not just in the UI.
6. **Secrets via env only.** Commit `.env.example`, never `.env`.

## v1 scope (held firm)

One edition (WC2026); Elo + historical + qualifier recency baseline; 5–10 preset conditions; 3–5 narrative packs; 3 report tiers (quick/analyst/executive); one orchestrator + one worker model; comparative top-3 mode. Everything else is deferred to "What's next."

## Orchestrator API contract

```
POST /simulations      {edition, mode, condition?, narrative_packs[], audience_scope[], report_tier} -> {run_id}
GET  /simulations/{id} -> {status, outcome?, narrative?, comparative?, confidence}
GET  /scenarios        -> [preset templates]
GET  /packs            -> [available context packs]
```

Internal: `outcome-engine POST /simulate`, `narrative-worker POST /run`.

## Testing approach

- **Unit:** strength/blend/recency functions; group ranking & tiebreakers; rejection filter per condition.
- **Integration:** `/simulate` against seeded test DB; `/run` against test Neo4j with deterministic fixtures; orchestrator job-state transitions.
- **E2E:** outcome-only → redistribution table; combined → assembled report with disclaimer.
- Mock only at edges (LLM providers, odds API). Never mock your own DB/graph.
- Type-check + lint in dev loop and CI.

## Guardrails (non-negotiable for credibility)

1. Persistent "scenario, not prediction" label on all narrative output (UI + API).
2. Low-confidence flags from thin `effective_runs`, sparse packs, or extreme conditions — carried engine → QC → UI.
3. Synthetic-content tagging on every generated post.
4. Polarization caveat in QC output and report: LLM crowds over-polarize vs reality; approach is unbenchmarked.
5. Cost ceiling enforced server-side.
