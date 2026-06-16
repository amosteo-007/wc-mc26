/* API client functions */

import type {
  SimulationResult,
  ScenarioTemplate,
  PackInfo,
  SelectionState,
  Team,
  TournamentState,
  MatchRequest,
  MatchResult,
} from "./types";

// In production (Render static site) NEXT_PUBLIC_API_URL is the orchestrator's
// full public URL (e.g. https://orchestrator.onrender.com). In local dev it's
// unset, so the Next.js rewrite proxy handles /api/* → localhost:8000.
const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "/api";

export async function createSimulation(
  selections: SelectionState
): Promise<{ run_id: string }> {
  const res = await fetch(`${BASE_URL}/simulations`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      edition: selections.edition,
      mode: selections.mode,
      condition: selections.condition,
      narrative_packs: selections.narrative_packs,
      audience_scope: selections.audience_scope,
      report_tier: selections.report_tier,
    }),
  });
  if (!res.ok) {
    throw new Error(`Failed to create simulation: ${res.status}`);
  }
  return res.json();
}

export async function getSimulation(
  id: string
): Promise<SimulationResult> {
  const res = await fetch(`${BASE_URL}/simulations/${id}`);
  if (!res.ok) {
    throw new Error(`Failed to fetch simulation: ${res.status}`);
  }
  return res.json();
}

export async function getScenarios(): Promise<ScenarioTemplate[]> {
  const res = await fetch(`${BASE_URL}/scenarios`);
  if (!res.ok) {
    throw new Error(`Failed to fetch scenarios: ${res.status}`);
  }
  const data = await res.json();
  return data.scenarios;
}

export async function getTeams(): Promise<Team[]> {
  const res = await fetch(`${BASE_URL}/teams`);
  if (!res.ok) {
    throw new Error(`Failed to fetch teams: ${res.status}`);
  }
  const data = await res.json();
  return data.teams;
}

export async function getTournament(): Promise<TournamentState> {
  const res = await fetch(`${BASE_URL}/tournament`);
  if (!res.ok) {
    throw new Error(`Failed to fetch tournament: ${res.status}`);
  }
  return res.json();
}

export async function runMatch(req: MatchRequest): Promise<MatchResult> {
  const res = await fetch(`${BASE_URL}/matches`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const err = await res.json();
      if (err?.detail) detail = err.detail;
    } catch {
      /* non-JSON error body */
    }
    throw new Error(detail);
  }
  return res.json();
}

export async function getPacks(): Promise<PackInfo[]> {
  const res = await fetch(`${BASE_URL}/packs`);
  if (!res.ok) {
    throw new Error(`Failed to fetch packs: ${res.status}`);
  }
  const data = await res.json();
  return data.packs;
}
