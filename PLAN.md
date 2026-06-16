# Build Plan — World Cup Outcome + Narrative Simulation Platform

This plan turns `world-cup-simulation-spec.md` into an ordered build. It is organized
into five phases. The first four are buildable largely in parallel after Phase 1's
schema lands; the fifth wires them into one runnable product.

## What this product is (one paragraph)

A constrained **forecasting console**. The user makes bounded selections (edition →
mode → condition → narrative packs → audience → report tier). A **Monte Carlo engine**
computes conditional tournament outcomes for the 2026 World Cup. A **GPT orchestrator**
turns the outcome into a world spec. A **cheap-model narrative worker** builds a
knowledge graph, instantiates a crowd of agents, runs a multi-round social simulation
(OASIS/MiroFish-style), and returns a stakeholder-reaction report. GPT does planning,
the world spec, QC, and final synthesis only — never per-agent generation. That split
is the core cost-control requirement.

## Verified facts the plan depends on

- **2026 format:** 48 teams, 12 groups of 4, top two per group + 8 best third-placed
  → Round of 32 → R16 → QF → SF → final; **104 matches** total (72 group + 32 knockout);
  champion plays 8 games. Group tiebreakers in FIFA order: points, goal difference,
  goals scored, head-to-head, fair play, drawing of lots. (FIFA; confirmed June 2026.)
- **MiroFish is real:** a multi-agent simulation engine built on **OASIS** (Open Agent
  Social Interaction Simulations, CAMEL-AI). Pipeline: knowledge-graph/GraphRAG build →
  persona generation → multi-round social sim → report agent. Runs on any
  OpenAI-compatible backend.
- **Two validity caveats** (drive the guardrails): the approach has **no published
  accuracy benchmarks**, and LLM agent crowds **polarize faster than real populations**.
  Narrative output is therefore a *scenario*, not a calibrated prediction.

## Tech stack (picked; redirect if you disagree)

| Layer | Choice | One-line reason |
|---|---|---|
| Outcome engine | Python + FastAPI, NumPy/SciPy | Vectorized Monte Carlo; numeric work belongs in Python |
| Orchestrator | Python + FastAPI, premium LLM | Conductor only; keeps premium tokens scarce |
| Narrative worker | Python + FastAPI, OASIS, cheap LLM | High-volume agent generation on a cheap model |
| Structured store | PostgreSQL | Teams, ratings, results, run state — tabular |
| Narrative graph | Neo4j | Entities/relations/topics — graph-shaped |
| Queue | Redis | Sims are long-running; UI polls run status |
| Frontend | Next.js (App Router) + TS + Tailwind | Constrained wizard, server-rendered results |

## Phase order

1. **[Data collection](docs/01-data-collection.md)** — what data, from where, in what shape.
2. **[Data pipeline](docs/02-data-pipeline.md)** — ingest → transform → validate → load.
3. **[Components](docs/03-components.md)** — the four backend services, built as vertical slices.
4. **[Frontend design](docs/04-frontend-design.md)** — the six-step wizard + results console.
5. **[Putting it together](docs/05-integration.md)** — end-to-end run, orchestration glue, guardrails, deploy.

## v1 scope (from the spec, held firm)

One edition (WC2026); one baseline sports model (Elo + historical + qualifier recency);
5–10 preset conditions; 3–5 narrative packs; 3 report tiers; one orchestrator + one
worker model; one comparative mode (top-3 likely winners). Everything else → "What's next."

## Milestones (each independently demoable)

- **M1** — Schema + seeded teams/ratings; outcome engine returns champion probs for the
  unconditional 2026 tournament. *(Phases 1–3, outcome slice)*
- **M2** — Conditional outcomes via rejection sampling; UI Steps 1–3 + champion
  redistribution table. *(Phases 3–4)*
- **M3** — One narrative pack runs end-to-end on a fixed winner world; sentiment +
  narrative clusters render. *(Phases 3–4)*
- **M4** — Full combined run through the orchestrator; comparative top-3 mode; guardrail
  labeling + confidence flags. *(Phase 5)*
