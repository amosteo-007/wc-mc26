# Phase 4 — Frontend Design

Goal: a **constrained forecasting console**, not a prompt box. Every input is a
dropdown, radio, or multi-select. The user explores bounded futures; they never author
a simulation from scratch. Config source of truth: `web/app/wizard.config.ts`.

> Pull visual direction from the `uiux-promax` user skill when implementing — this doc
> covers structure and behavior, not pixels.

## Why constrained (keep this in mind while building)
The narrative layer needs clean graph inputs and explicit prediction targets; MiroFish-
style workflows are strongest when scope is bounded. Free-text would break graph
construction and blow the cost budget. The UI's job is to keep inputs structured.

## The six-step wizard (maps 1:1 to the spec)

1. **Tournament** — edition + mode select. v1: WC2026 only. Show the format inline
   (48 teams / 12 groups / 104 matches) so the user knows the world they're simulating.
2. **Simulation type** — radio: `outcome` | `narrative` | `combined`. This gates which
   later steps appear (narrative-only skips conditions; outcome-only skips packs).
3. **Condition builder** — single-select from the preset library (team exits group,
   reaches QF, wins, host underperforms, underdog semifinal, penalty final, refereeing
   controversy). Each maps to a Monte Carlo constraint — the user never writes logic.
4. **Narrative packs** — multi-select reaction layers (sponsor, fan, media, online,
   political, tourism/business). Each maps to a stakeholder graph + report section.
5. **Audience scope** — multi-select lenses (domestic winner, rival, neutral, sponsors,
   host media, regional LATAM/EUR/APAC/MENA). Determines which agents get instantiated.
6. **Report tier** — radio: quick | analyst | executive. Drives runs, agent count,
   rounds, and synthesis depth. Show the cost/latency trade-off honestly at this step.

**Wizard behavior**
- Linear with back-nav; selections persisted in URL/query so a run is shareable.
- Validate per step; disable "Run" until required selections exist.
- Surface estimated latency/cost from the chosen tier before submit.

## Results console (two panels)

**Quantitative**
- Champion redistribution table (condition vs base odds).
- Most likely finalists; top alternate bracket paths; upset frequencies.
- A prominent **confidence** note (from outcome `confidence` + `effective_runs` — warn
  loudly when a rare condition left few surviving rollouts).

**Qualitative**
- Sentiment heatmap by audience/allegiance.
- Dominant narrative clusters (top 5 themes).
- Sponsor response matrix (scenario × severity).
- Media framing by region.
- 24h / 72h / 7d narrative timeline; turning points / flashpoints.
- Sample synthetic posts — **clearly labeled synthetic**.

**Comparative mode (v1)**
When multiple likely winners are simulated, render side-by-side narrative outcomes
("Spain wins" vs "England wins") so the user compares sporting likelihood *and*
downstream comms risk in one view.

## Async UX
Runs are long. Submit → run page with live status (queued → outcome done → narrative
running → synthesizing). Stream the quantitative panel as soon as the outcome finishes;
fill the qualitative panel when the narrative completes. Never spin a blank screen.

## Mandatory labeling (guardrail in the UI itself)
A persistent banner on every narrative result: **"Scenario simulation, not a
prediction."** Outcome probabilities and narrative reactions are epistemically
different — the UI must not let them read as equally validated. Show low-confidence
flags inline where the narrative is sensitive to sparse packs or extreme conditions.

## Component tree (sketch)
```
app/
  wizard/ (Step1..Step6, useWizardState)
  run/[id]/ (StatusBar, QuantPanel, QualPanel, ComparativeView, ConfidenceBadge, SimDisclaimer)
  components/ (Select, RadioGroup, MultiSelect, Heatmap, RedistributionTable, Timeline)
```

## Deliverables for Phase 4
- Working six-step wizard driving the `POST /simulations` contract.
- Results console rendering quant + qual + comparative from a completed run.
- Disclaimer banner + confidence/low-confidence flags wired to real fields.
