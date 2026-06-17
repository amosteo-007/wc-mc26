# Deploy: Monte Carlo console on Render (free tier)

Publish the Monte Carlo engine (tournament + match simulator) on Render — no
servers to administer, no Docker. **Outcome engine only** (`MC_ONLY=true`): the
narrative worker, Neo4j, and LLM-driven simulation are excluded from this
deployment. The whole stack is defined in [`render.yaml`](render.yaml) as a
Render Blueprint, so deploy is: push to GitHub → connect the blueprint → set the
one secret → done.

## Architecture on Render

```
Browser ──HTTPS──> wc2026 (static site)         ──API calls──> wc2026-api (orchestrator)
                   /run/* → SPA shell rewrite                       │
                                                                    └──> wc2026-engine (outcome-engine) ──> Postgres
                                                                              │
                                                                              └──> Redis (rate-limit state)
```

| Render service | Type | Plan | Notes |
|---|---|---|---|
| `wc2026` | Static Site | free | Next.js static export (`web/out`); calls the API directly via `NEXT_PUBLIC_API_URL`. |
| `wc2026-api` | Web Service (Python) | free | Public API: validation, rate limiting, CORS. `MC_ONLY=true`. |
| `wc2026-engine` | Web Service (Python) | free | NumPy Monte Carlo. Reached only by the orchestrator. |
| `wc2026-postgres` | Managed Postgres | free | Teams, ratings, format, match history, results. |
| `wc2026-redis` | Key Value (Redis) | free | Rate-limit + concurrency counters. |

Render auto-provisions HTTPS for every service. Free web services **spin down
after ~15 min idle** and cold-start on the next request (~30–60s) — fine for a
demo, not for low-latency production.

## Repo changes (already in place)

| File | Change |
|---|---|
| [`render.yaml`](render.yaml) | Blueprint defining all five services + their env wiring. |
| [`web/next.config.mjs`](web/next.config.mjs) | `output: 'export'` when `NEXT_PUBLIC_API_URL` is set; local-dev `/api` rewrite otherwise. |
| [`web/lib/api.ts`](web/lib/api.ts) | `BASE_URL` ← `NEXT_PUBLIC_API_URL ?? "/api"`. |
| `web/app/run/[id]/` | Split into a server `page.tsx` (`generateStaticParams`) + client `RunResults.tsx`, so the dynamic route survives static export. |
| [`services/orchestrator/main.py`](services/orchestrator/main.py) | `MC_ONLY=true` strips narrative/combined scenarios, rejects non-outcome modes (422). |

## Deploy steps

1. **Push to GitHub.** Render reads the blueprint from the repo root.

2. **New Blueprint.** Render dashboard → **New → Blueprint** → select the repo.
   Render parses `render.yaml` and lists the five resources. Click **Apply**.
   It provisions Postgres + Redis, then builds and deploys each service, wiring
   `POSTGRES_URL` / `REDIS_URL` automatically.

3. **Set the LLM secret.** In the `wc2026-api` service → **Environment**, set
   `PREMIUM_API_KEY` (marked `sync: false` so it's never in the repo). With
   `MC_ONLY=true` no LLM is actually called, so a placeholder is fine — but the
   orchestrator reads the key to decide whether premium features are enabled.

4. **Confirm cross-service URLs.** The blueprint sets these to the conventional
   Render hostnames; if you renamed any service, update them under **Environment**:
   - `wc2026-api`: `OUTCOME_ENGINE_URL=https://wc2026-engine.onrender.com`,
     `ALLOWED_ORIGINS=https://wc2026.onrender.com`
   - `wc2026` (static): `NEXT_PUBLIC_API_URL=https://wc2026-api.onrender.com`

5. **Load schema + seed data.** Open the Postgres instance → **Connect** → copy
   the external `psql` command, then from the repo root:
   ```bash
   for f in data/schema/schema.sql data/seed_teams.sql data/seed_ratings.sql \
            data/seed_format.sql data/seed_matches.sql data/seed_wc_results.sql; do
     psql "$RENDER_POSTGRES_EXTERNAL_URL" -f "$f"
   done
   ```
   (One-time. The free Postgres external URL works from your laptop.)

6. **Redeploy the API + frontend** if you changed any URL in step 4 (Render
   rebuilds the static site so `NEXT_PUBLIC_API_URL` is baked into the bundle).

Visit `https://wc2026.onrender.com`.

## Verify

```bash
API=https://wc2026-api.onrender.com
curl $API/health                       # {"status":"ok","service":"orchestrator"}
curl $API/scenarios                     # outcome presets only (MC_ONLY)
curl -X POST $API/matches -H 'Content-Type: application/json' \
     -d '{"home_fifa_code":"IRN","away_fifa_code":"NZL","goal_line":3}'   # full breakdown
curl -X POST $API/simulations -H 'Content-Type: application/json' \
     -d '{"mode":"combined","report_tier":"quick"}'                       # 422 (combined rejected)
```

Then in a browser: a tournament sim → redistribution table renders; the match
simulator (IRN vs NZL, goal line 3) → full breakdown; refresh a `/run/<id>`
page directly → it still loads (SPA rewrite).

## Updating live results (group stages + knockout)

Group standings and the knockout bracket are **computed from match results** in
the `wc_results` table — you never edit standings or the bracket directly. Drop
in match scores and everything re-derives: group points/GD/rank, the 8 best
third-placed teams, and the bracket auto-advances each winner from R32 → Final.

**Where scores come from.** Set `WC_RESULTS_SOURCE=fifa` (in `render.yaml`) to
pull from FIFA's API (`api.fifa.com`, unofficial), or `WC_RESULTS_URL` for your
own JSON feed in the `{edition, matches:[...]}` shape.

**How to trigger a refresh.** `POST /admin/refresh`, guarded by the `ADMIN_TOKEN`
secret (set it to a long random string in the Render dashboard; unset = endpoint
disabled). No always-on worker needed — fits free tier.

```bash
API=https://wcmontecarlosim-api.onrender.com
# Pull latest from the configured source (FIFA):
curl -X POST $API/admin/refresh -H "X-Admin-Token: $ADMIN_TOKEN"
# …or submit/correct scores by hand (same endpoint, JSON body):
curl -X POST $API/admin/refresh -H "X-Admin-Token: $ADMIN_TOKEN" \
     -H 'Content-Type: application/json' \
     -d '{"edition":"WC2026","matches":[
           {"stage":"R32","matchday":1,"home":"ARG","away":"USA",
            "home_goals":2,"away_goals":1,"played_on":"2026-06-30"}]}'
```

A level knockout score needs a `"shootout_winner":"<CODE>"` to advance the
bracket (otherwise that tie stays TBD).

**Automate it (optional).** Point a free external scheduler at the endpoint on
matchdays — e.g. [cron-job.org](https://cron-job.org) or a GitHub Actions
`schedule:` workflow doing the same `curl`. (Render's own Cron Jobs are a paid
feature; the external-cron route stays $0.)

## Cost & limits

Everything above is **Render free tier** ($0). Trade-offs: web services sleep
when idle (cold starts), free Postgres is capped (1 GB, expires after 90 days
unless upgraded), and there's no horizontal scaling. To remove the cold start,
bump the two web services to the Starter plan ($7/mo each). The narrative
worker + Neo4j (the LLM path) are intentionally out of scope here — they need
paid plans and are a separate deployment.
