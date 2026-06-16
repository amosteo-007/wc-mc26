# Plan: Match-level Monte Carlo + transfer/news narrative + production guardrails

## Context

Two new user-facing capabilities, plus the essential hardening needed to open
the console to the public:

1. **Single-match Monte Carlo.** Users want to ask match questions —
   e.g. "how likely are 3 goals between Iran and New Zealand" — answered by
   Monte Carlo over the existing Poisson goal model, grounded in team Elo +
   recent form. Today the engine only simulates whole tournaments.

2. **Narrow the narrative to transfer value + news.** The current narrative
   simulates broad stakeholder reactions (fan/sponsor/media/political). The user
   wants to **replace** that with a focused "transfer value & football news"
   narrative: after a team wins or performs well, agents react with
   transfer-rumor / player-market / news posts. Grounding is **LLM-generated
   from each team's pack `stars` list** (cheap model), with template fallback.

3. **Essential production guardrails** (decided scope — not full auth/queue):
   server-side enforcement of tier/run caps, input validation + whitelisting,
   per-IP rate limiting, locked-down CORS, and bounded match `n_runs`. Defers
   accounts/API-keys, a real job queue, secrets manager, and prod Docker to a
   follow-up.

The goal model (`compute_goal_expectations` + `simulate_match_goals`) and form
adjustment (`compute_form_adjustment`) already exist and are reused as-is.

---

## Part 1 — Single-match Monte Carlo (outcome engine)

### 1a. New DB query — `services/outcome-engine/database.py`
`get_recent_matches` only returns games where **both** teams are in the list, so
it can't supply form for an arbitrary pair. Add:
- `get_team_by_code(code)` → `{id, fifa_code, name, confederation}` (or None).
- `get_matches_for_teams(team_codes, since_date='2023-01-01', limit=500)` —
  matches where **either** home or away is in `team_codes` (drop the second
  `ANY` filter to one side OR'd). Used to compute each team's form vs. any
  opponent for the single match. Same row shape as `get_recent_matches`.

### 1b. Match simulation function — `services/outcome-engine/models/match_sim.py` (new)
`simulate_match(home_elo, away_elo, n_runs, neutral, is_host_home, seed)`:
- Loop `n_runs`: `compute_goal_expectations(...)` (pass `home_advantage=0` when
  `neutral=True`) → `simulate_match_goals(...)`. Reuse `models/strength.py`
  verbatim — no new goal math.
- Aggregate into a **full breakdown** (the chosen output):
  - `win_home` / `draw` / `win_away` probabilities,
  - `expected_goals_home` / `expected_goals_away` / `expected_total`,
  - `total_goals_distribution`: `{0,1,2,3,4,5+}` → prob,
  - `over_under`: P(total ≥ line) for lines 0.5–4.5 (and matching under),
  - `both_teams_score` probability,
  - `top_scorelines`: most-frequent `"H-A"` scorelines with prob,
  - `goal_line_query`: if a `goal_line` param is supplied, echo
    `P(total_goals ≥ goal_line)` so the literal "3 goals" question is answered
    directly.
- Return dict + a `confidence` block (n_runs, rating_coverage, whether form was
  applied) mirroring the tournament response style.

Form: assemble `home_elo`/`away_elo` like `run_simulation` does (mean of
ratings, fallback 1800) and apply `compute_form_adjustment([home,away], elos,
matches)` from `models/simulator.py` using `get_matches_for_teams`.

### 1c. Endpoint — `services/outcome-engine/main.py`
- `MatchRequest` Pydantic model with **bounded** fields:
  `home_fifa_code: str`, `away_fifa_code: str`,
  `n_runs: int = Field(20000, ge=1000, le=200000)`,
  `neutral: bool = True`, `goal_line: Optional[float] = Field(None, ge=0, le=15)`,
  `seed: Optional[int]`.
- `POST /simulate/match`: look up both teams (404 if either code unknown),
  fetch ratings + form matches, call `simulate_match`, return a
  `MatchResponse`. Validate the two codes differ.
- Reuse existing `data_version` stamping.

### 1d. Tests — `services/outcome-engine/tests/test_match_sim.py` (new)
- Higher-Elo team wins more often than it loses over many runs.
- Probabilities sum to ~1 (win+draw+loss); total-goals distribution sums ~1.
- `goal_line=3` returns a sane `P(≥3)` in (0,1); neutral vs. host flips home edge.
- Follow the seed-loading pattern in `tests/test_simulator.py` (no DB needed —
  pass elos directly to `simulate_match`).

---

## Part 2 — Orchestrator wiring + match request shape

The orchestrator is the only public API, so the match feature is exposed there
too (the engine isn't public-facing).
- `services/orchestrator/models.py`: add `MatchRequest`/`MatchResponse` mirrors
  (bounded the same way).
- `services/orchestrator/main.py`: add `POST /matches` that proxies to outcome
  engine `POST /simulate/match` (httpx, short timeout — match sim is fast/sync,
  no background job needed). Apply the rate limiter (Part 3).
- This is **synchronous** (returns the breakdown directly), unlike tournament
  runs — match sim of 20k runs is milliseconds.

---

## Part 3 — Narrow the narrative to transfer value + news (REPLACE)

Replace the broad stakeholder simulation with a transfer/news focus. Keep the
multi-round + sentiment + cluster scaffolding; change **what agents are and what
they talk about**.

### 3a. Personas — `services/narrative-worker/persona.py`
Replace the 9 stakeholder archetypes with a transfer/news cast, e.g.:
`transfer_insider`, `club_scout`, `selling_club_fan`, `buying_club_fan`,
`agent_source`, `beat_reporter`, `market_analyst`, `rumor_aggregator`,
`casual_follower`. Keep the influence/network/stance machinery.

### 3b. Topics — `services/narrative-worker/graph_builder.py`
Replace the hardcoded 8 topics with transfer/news topics: `transfer_rumor`,
`market_value_shift`, `release_clause`, `bidding_war`, `contract_renewal`,
`breakout_player`, `agent_movement`, `news_break`.

### 3c. Posts — `services/narrative-worker/simulation.py`
- Replace `POST_TEMPLATES` with transfer/news templates per new archetype
  (all `[SYNTHETIC]`-tagged), using `{team}`, `{player}`, `{value}` slots.
- `generate_post`: when the cheap model is available, build the prompt from the
  **winning team's pack `stars`** (passed through `world_spec`) so posts name
  real squad players and plausible value moves; the LLM is instructed to stay on
  transfer-value/news and tag `[SYNTHETIC]`. Template fallback when no key.
- Rework `compile_narrative_clusters` to transfer/news clusters
  (e.g. "Breakout star value surge", "Bidding war rumors", "Contract standoff").
- Trim the now-irrelevant pack-based sentiment branches; drive the arc from
  winner popularity/underdog status (a breakout underdog → bigger value-surge
  buzz). Drop `sponsor_matrix`/`media_tone` from this focused report (or keep a
  minimal `news_volume` series).

### 3d. World spec carries player context — `services/orchestrator/world_spec.py`
Add `winner_stars: [..]` to the world spec by reading the winner's team pack
(`packs/team/<CODE>.json` → `payload.stars`). Pass through orchestrator →
worker so post generation can name players. Add `narrative_scope:
"transfer_news"`.

### 3e. Wizard + results — `web/`
- `wizard.config.ts`: replace `NARRATIVE_PACKS` stakeholder list with the
  transfer/news framing (the mode now produces transfer/news output); update
  Step-2/Step-4 copy ("Narrative = transfer value & football news").
  `MODES` narrative description updated.
- Results page (`web/app/run/[id]/page.tsx`) + `web/lib/types.ts`: relabel the
  narrative section to "Transfer & News Reactions"; cluster labels already come
  from the worker. Keep the `[SYNTHETIC]` tags and the scenario disclaimer.
- Update `PRESET_SCENARIOS` in orchestrator `main.py` to the new framing.

> Note: this is a **replacement**, so the old sponsor/fan/political pack ids stop
> being meaningful. Whitelist (Part 4) is updated to the new scope ids; old
> packs remain on disk but are no longer wired into the narrative output.

---

## Part 4 — Essential production guardrails

### 4a. Enforce tier caps server-side — `services/orchestrator/main.py` + `models.py`
- In `create_simulation`, derive `n_runs` (and agent/round budgets) **only** from
  `TIER_BUDGET[report_tier]` — never trust a client-supplied value. The worker
  already takes tier; pass the capped budget explicitly and have the worker clamp
  `n_agents`/`n_rounds` to the tier ceiling (`narrative-worker/main.py`).
- Add a `CHECK` (or app-level clamp) so `sim_runs.n_runs` can't exceed the
  executive ceiling.

### 4b. Input validation + whitelisting — `services/orchestrator/models.py`
- `SimulationRequest`: `narrative_packs`/`audience_scope` →
  `List[str] = Field(default_factory=list, max_length=N)`; reject values not in
  the known scope whitelist (return 422). Validate `condition.type` is a known
  preset and `team_fifa_code` exists. Bound `MatchRequest` as in 1c.
- Replace bare `HTTPException(500, str(e))` with generic messages (don't leak
  internals); log the detail server-side.

### 4c. Rate limiting — orchestrator
- Add `slowapi` (or a small Redis token-bucket using the existing Redis client)
  limiter: per-IP caps, e.g. `POST /simulations` and `POST /matches` limited
  (matches looser since they're cheap). Add `slowapi` to
  `services/orchestrator/requirements.txt`. Return 429 on exceed.
- Cap concurrent background sim jobs with a Redis counter (reject with 429 when
  global in-flight ≥ ceiling) so a public user can't spawn unbounded tournament
  runs. (Lightweight; full job-queue deferred.)

### 4d. CORS — orchestrator
- Replace `allow_origins=["*"]` with an env-driven allowlist
  (`ALLOWED_ORIGINS`, comma-separated; default to localhost for dev). Add to
  `.env.example`.

> Explicitly deferred (documented, not built this round): end-user API-key auth,
> Celery/RQ job queue, secrets manager, prod Docker (`--reload` removal,
> workers, healthchecks), Next.js API proxy via env. Listed in the PR summary as
> "before full public launch".

---

## Critical files

- Engine: `services/outcome-engine/main.py`, `models/match_sim.py` (new),
  `models/strength.py` (reuse), `models/simulator.py` (`compute_form_adjustment`
  reuse), `database.py`, `tests/test_match_sim.py` (new).
- Orchestrator: `main.py`, `models.py`, `world_spec.py`,
  `requirements.txt`, `.env.example`.
- Narrative worker: `persona.py`, `graph_builder.py`, `simulation.py`,
  `main.py`.
- Web: `web/app/wizard/wizard.config.ts`, `web/app/wizard/page.tsx`,
  `web/app/run/[id]/page.tsx`, `web/lib/api.ts`, `web/lib/types.ts`, and a new
  match UI (a wizard entry or a dedicated `/match` page with a two-team picker +
  goal-line input rendering the breakdown card).

## Verification

1. **Engine unit tests**: `cd services/outcome-engine && python -m pytest tests/`
   → match-sim tests pass (host edge, prob sums, goal-line).
2. **Match endpoint** (stack up): `curl -s -X POST localhost:8000/matches -d
   '{"home_fifa_code":"IRN","away_fifa_code":"NZL","goal_line":3}'` → returns
   win/draw/loss, total-goals distribution, and `P(total ≥ 3)`.
3. **Caps**: POST a tournament sim with a tampered large `n_runs` → server clamps
   to the tier ceiling (inspect `sim_runs.n_runs`). Exceed the rate limit → 429.
   Unknown `narrative_pack`/team code → 422.
4. **Narrative**: run a combined sim with a winner that has a team pack (e.g.
   BRA) → narrative posts/clusters are transfer/news themed, name squad players,
   all `[SYNTHETIC]`-tagged; broad sponsor/fan output is gone.
5. **CORS**: request from a disallowed origin is blocked; allowed origin works.
6. **Web typecheck**: `cd web && npx tsc --noEmit` → exit 0; match page renders
   the breakdown; narrative section relabeled "Transfer & News".
