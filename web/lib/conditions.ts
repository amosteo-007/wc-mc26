/* Human-readable labels for conditions + stage-probability lookup helpers. */

import type { Condition } from "./types";

const TEAM_STAGE: Record<string, { stage: string; verb: string }> = {
  team_reaches_r16: { stage: "R16", verb: "reaches the Round of 16" },
  team_reaches_qf: { stage: "QF", verb: "reaches the quarter-finals" },
  team_reaches_sf: { stage: "SF", verb: "reaches the semi-finals" },
  team_reaches_final: { stage: "final", verb: "reaches the final" },
  team_wins: { stage: "champion", verb: "wins the World Cup" },
};

/** A plain-language sentence describing the simulated condition. */
export function describeCondition(condition?: Condition | null): string {
  if (!condition || !condition.type) return "Unconditional — full tournament";
  const team = condition.params?.team_fifa_code;
  const ts = TEAM_STAGE[condition.type];
  if (ts && team) return `${team} ${ts.verb}`;

  switch (condition.type) {
    case "team_exits_group":
      return `${team ?? "Selected team"} exits in the group stage`;
    case "host_underperforms":
      return "All three host nations fail to advance";
    case "underdog_semifinal":
      return "An underdog (Elo < 1900) reaches the semi-finals";
    case "penalty_final":
      return "The final is decided by a penalty shootout";
    case "refereeing_controversy":
      return "A major refereeing controversy (narrative-only — not modeled numerically)";
    default:
      return condition.type;
  }
}

/** True when the condition has no numeric effect on the outcome distribution. */
export function isNonNumericCondition(condition?: Condition | null): boolean {
  return condition?.type === "refereeing_controversy";
}

/**
 * For a team-stage condition, return {team, stage, label} so the UI can show
 * the unconditional probability of that exact event. null for other conditions.
 */
export function conditionStageTarget(
  condition?: Condition | null
): { team: string; stage: string; verb: string } | null {
  if (!condition?.type) return null;
  const team = condition.params?.team_fifa_code;
  const ts = TEAM_STAGE[condition.type];
  if (ts && team) return { team, stage: ts.stage, verb: ts.verb };
  return null;
}
