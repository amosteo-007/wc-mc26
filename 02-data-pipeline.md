# Phase 2 — Data Pipeline

Goal: a repeatable ETL that turns raw sources into the simulation-ready Postgres tables
and compiled context packs, with quality gates that produce the **confidence flags** the
product surfaces to users. Lives in `pipeline/`.

## Stages

```
ingest/    -> transform/    -> validate/        -> load/
(pull raw)    (clean/blend)    (quality gates)     (upsert Postgres + packs)
data/raw      data/processed   confidence report   teams, ratings, history, format,
                                                    context_packs
```

### ingest/
- One module per source. Output raw, immutable snapshots to `data/raw/<source>/<date>/`.
- Be defensive: sources change schemas and go offline. Snapshot, then parse — never
  parse live.
- Record provenance (source, URL, pulled_at, row count) for every pull.

### transform/
- Normalize team identities to a single `fifa_code` (the join key everywhere).
- Dedupe historical results; reconcile conflicting scores across sources.
- **Recency weighting:** weight matches by age; up-weight qualifier-era results.
  Make the weighting function explicit and testable — it materially moves odds.
- **Strength blending (premium tier):** when odds/market-values are present, blend them
  into the Elo prior. Keep the blend a single documented function so it can be A/B'd.
- Output tidy parquet/CSV to `data/processed/`.

### validate/  (this is where confidence flags are born)
Gates run before load; failures block load and annotate `confidence`:
- **Coverage** — every 2026 qualified team has a current rating and ≥N recent matches.
- **Freshness** — ratings `as_of` within an acceptable window of kickoff.
- **Schema** — types, non-null keys, score sanity (no negative goals, plausible ranges).
- **Cross-source consistency** — rating disagreement across sources within tolerance;
  large disagreement → low-confidence flag on that team, surfaced in outcome `confidence`.

### load/
- Idempotent upserts into `teams`, `ratings`, `matches_history`, `tournament_format`.
- Compile authored `packs/**/*.json` into `context_packs` (versioned; never overwrite a
  prior version — insert a new one so runs are reproducible).

## Orchestration & cadence
- Scheduler: cron for v1; graduate to Dagster/Airflow if dependencies grow.
- Cadence: ratings + results **daily** in the run-up; format/packs **on change**.
- Each run emits a data-quality report archived alongside the snapshot, so any
  simulation can be traced to the exact data version it used.

## Reproducibility requirement
A simulation must be re-runnable against the same inputs months later. Pin a
`data_version` (snapshot date + pack versions) onto every `sim_run`. This is what lets
the product honestly attach confidence to an outcome.

## Deliverables for Phase 2
- Working `ingest → transform → validate → load` for the **mandatory** numeric inputs.
- Pack compiler loading `packs/` into `context_packs`.
- A data-quality report artifact + `data_version` stamping on runs.

## Tests (wire in now, not later)
- Unit: recency-weighting and strength-blend functions on fixed inputs.
- Integration: load into a real test Postgres; assert coverage gate catches a missing team.
