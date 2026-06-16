# Phase 1 — Data Collection

Goal: identify every data input, name candidate sources, define the target shape, and
flag licensing. Two very different kinds of data: **numeric** (outcome engine) and
**authored context** (narrative engine). Do not conflate them.

## 1A. Outcome-engine data (numeric)

| Element | Purpose | Tier | Candidate source (verify license before use) |
|---|---|---|---|
| Team Elo / SPI-style rating | Baseline strength | Mandatory | World Football Elo Ratings (eloratings.net); any equivalent national-team rating |
| Historical national-team results | Form + score-model fit | Mandatory | Public "international football results" datasets (e.g. martj42/international_results on GitHub/Kaggle) |
| 2026 format + bracket + tiebreaks | Path rules | Mandatory | FIFA official format pages (encode once into `tournament_format.spec`) |
| WC qualifier results | Recent / qualification-stage form | Mandatory (v1) | Same results datasets, filtered to `competition='wc_qualifier'` |
| Bookmaker odds | Calibration + blended prior | Optional premium | A licensed odds API (e.g. the-odds-api); requires key + ToS check |
| Squad market values | Talent proxy | Optional premium | Transfermarkt (scraping ToS-restricted — license required) |
| Player ratings / plus-minus | Team quality proxy | Optional premium | Vendor rating feeds (commercial) |
| Match location / host effects | Venue adjustment | Optional | Host-city schedule (US/Canada/Mexico venues) |

**Notes that matter for correctness:**
- Sources above are *candidates*. Each must have its license/ToS verified before
  ingestion — several football data sources prohibit redistribution or scraping.
- Ratings are dated snapshots: store `as_of` and always simulate from the latest
  snapshot before kickoff. Recency-weight historical results, with qualifier-era
  matches up-weighted (per the product brief).
- Calibrate the Poisson/strength mapping (`models/strength.py`) against held-out
  historical tournaments — don't ship the placeholder coefficients.

## 1B. Narrative-engine data (authored context packs)

These are **written and curated**, not scraped. They become the seed material the
graph builder turns into entities/agents. Store as versioned JSON in `packs/` and load
into `context_packs`. Build packs for all major teams + tournament archetypes up front
so the user flow stays simple.

| Pack | Contents | Drives |
|---|---|---|
| Team | Legacy, star players, current public narrative, rivalries | Meaning of a given winner |
| Sponsor | Brand sensitivity, campaign goals, risk tolerance, regional exposure | Sponsor reaction |
| Fan | Domestic / rival / neutral archetypes, ultras vs casual split | Sentiment diversity |
| Media | Broadcaster priorities, journalist lenses, likely headline angles | Press framing |
| Political | Symbolism, identity sensitivities, state-messaging hooks | National / policy angle |
| Online platform | Posting norms, amplification dynamics, conflict propensity | Narrative propagation |

**Target JSON shape (per pack file):**
```json
{
  "pack_type": "team", "entity_key": "BRA", "version": 1,
  "payload": { "legacy": "...", "stars": ["..."], "rivalries": ["ARG"],
               "current_narrative": "...", "stance_priors": {} }
}
```

**Editorial guardrail:** political and sponsor packs touch real institutions and real
public figures. Keep packs to *archetypes and documented public positioning*; do not
fabricate quotes attributed to named real people. The simulation produces *fictional*
agents reacting — label all generated posts as synthetic.

## Deliverables for Phase 1
- `data/schema/schema.sql` populated source list and a per-source license note.
- ≥1 authored pack per type committed to `packs/` as the schema reference example.
- A one-page source register (source, URL, license, refresh cadence, owner).

## Open questions to resolve before Phase 2
- Which rating source is canonical for v1, and is its license redistribution-safe?
- Is any premium tier in v1, or are odds/market-values deferred to "What's next"?
