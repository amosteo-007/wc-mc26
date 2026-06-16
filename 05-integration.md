# Phase 5 — Putting It All Together

Goal: one end-to-end `combined` run, from wizard submit to assembled report, with the
cost split, guardrails, tests, and deploy in place.

## End-to-end run (the seven-stage pipeline)

```
[web wizard]
   │  POST /simulations  (bounded selections)
   ▼
[orchestrator] ── validate ── enqueue ──▶ run_id (UI starts polling)
   │ 1. planner: selections → MC Condition + packs + budget        (premium, small)
   ▼
[outcome-engine] /simulate
   │ 2. Monte Carlo under condition (rejection sampling) → champion/finalist/paths
   ▼
[orchestrator]
   │ 3. choose world(s): 1 for quick, top-3 for comparative
   │ 4. world_spec: structured control file                        (premium, small)
   ▼
[narrative-worker] /run                                            (cheap model only)
   │ 5. graph_builder → Neo4j   6. persona → crowd variants
   │ 7. simulation → N rounds   8. report → structured intermediate
   ▼
[orchestrator]
   │ 9. qc: validate vs metrics, flag low-confidence
   │10. synthesize final report                                    (premium, small)
   ▼
[web run page]  quant panel (streamed early) + qual panel + comparative + disclaimer
```

**Premium-model touchpoints:** steps 1, 4, 9, 10 — and nowhere else. Everything inside
the round/agent loops is the cheap worker. This is the architecture's whole point.

## Orchestration glue
- Redis-backed job with explicit states: `queued → outcome_running → outcome_done →
  narrative_running → synthesizing → done|failed`. UI polls `GET /simulations/{id}`.
- Stream the quantitative result the moment the outcome finishes (don't wait on narrative).
- Stamp `data_version` (Phase 2) onto every run for reproducibility.
- Persist intermediates (world_spec, round state) so a failed synthesis can retry without
  re-running the sim.

## Guardrails (the product's credibility depends on these)
1. **Label narrative as scenario, not prediction** — persistent UI banner + a flag on the
   API response. Outcome probs and narrative reactions are not the same kind of claim.
2. **Low-confidence surfacing** — thin `effective_runs`, sparse packs, or extreme
   conditions raise flags carried from engine → QC → UI.
3. **Synthetic-content labeling** — every generated post tagged synthetic; no fabricated
   quotes attributed to real named people in packs or output.
4. **Polarization caveat** — note in QC output that LLM crowds over-polarize vs reality
   and the approach is unbenchmarked; the report states this in plain language.
5. **Cost ceiling** — tier caps (runs/agents/rounds) enforced server-side, not just in UI.

## Testing (testing pyramid)
- **Unit:** strength/blend/recency functions; group ranking & tiebreakers; rejection
  filter for each preset condition.
- **Integration:** `/simulate` against seeded test DB; `/run` against a test Neo4j with a
  stub cheap-model (deterministic fixtures); orchestrator job-state transitions.
- **E2E (one per critical flow):** outcome-only run → redistribution table; combined run →
  assembled report with disclaimer present.
- Mock only at the edges (LLM providers, odds API). Never mock your own DB/graph.
- Type-check + lint in the dev loop and in CI.

## Deployment & CI/CD
- Containerize the three backend services (`docker-compose.yml` for local; same images to
  the cloud). Frontend → Vercel or a container, your call.
- CI on every push: install, lint, typecheck, test, build; block merge on failure.
- CD: `main` → staging automatically; tagged release → prod with approval.
- DB migrations run as part of deploy, not by hand. Secrets in the platform store.

## Operations
- Structured logs + error tracking (Sentry-class) from the first endpoint.
- Daily Postgres backups with a **tested** restore; Neo4j export on a schedule.
- Runbook: deploy, roll back, rotate a model key, what to do if a sim wedges in `running`.
- Token/cost dashboard split by premium vs cheap model — the one metric that proves the
  architecture is doing its job.

## Definition of done for v1
A user runs "Brazil exits in the group stage → combined report, sponsor + fan + media
packs, executive tier, top-3 comparative," and gets: revised champion odds with
confidence, three side-by-side winner-narrative worlds, sentiment/sponsor/media
breakdowns, a 24h/72h/7d timeline, sample synthetic posts, and an unmissable
"scenario, not prediction" label — produced within the tier's cost/latency budget.

## What's next (deferred, called out honestly)
- More editions (Euros, Copa, club competitions) and a richer sports model.
- Premium data tier on by default (odds/market-values/player ratings) once licensed.
- Interactive "god's-eye" mode (query individual agents mid-run), as MiroFish supports.
- Accuracy backtesting once any ground truth exists — until then, no calibration claims.
- AuthN/AuthZ, multi-tenancy, saved/shareable reports — none built until asked.
