/* TypeScript types for all data shapes */

export interface Team {
  fifa_code: string;
  name: string;
  confederation: string;
}

export interface GroupStanding {
  team: string;
  name: string;
  p: number;
  w: number;
  d: number;
  l: number;
  gf: number;
  ga: number;
  gd: number;
  pts: number;
  rank: number;
}

export interface GroupMatch {
  home: string;
  away: string;
  home_goals: number;
  away_goals: number;
  matchday: number;
  played_on: string | null;
}

export interface GroupState {
  group: string;
  standings: GroupStanding[];
  matches: GroupMatch[];
  played: number;
}

export interface BracketTie {
  match: number;
  home: string;
  away: string;
  slot?: string | null;
  desc?: string;
}

/** A bracket tie resolved against live results: placeholder labels become real
 *  FIFA codes once the feeder match is played; null = still TBD. */
export interface ResolvedTie {
  match: number;
  home: string; // placeholder label (e.g. "1A", "W32-1")
  away: string;
  home_code: string | null; // resolved team code, or null (TBD)
  away_code: string | null;
  played: boolean;
  home_goals: number | null;
  away_goals: number | null;
  winner: string | null;
  desc?: string;
}

export interface ResolvedBracket {
  R32?: ResolvedTie[];
  R16?: ResolvedTie[];
  QF?: ResolvedTie[];
  SF?: ResolvedTie[];
  "3rd_place"?: ResolvedTie;
  Final?: ResolvedTie;
  best_thirds?: { team: string; group: string; pts: number; gd: number; gf: number }[];
  champion?: string | null;
}

export interface TournamentState {
  edition: string;
  groups: GroupState[];
  knockout_bracket: { R32?: BracketTie[] } & Record<string, unknown>;
  knockout?: ResolvedBracket;
  group_stage_complete: boolean;
  champion?: string | null;
}

export interface Condition {
  type: string;
  params: Record<string, string>;
}

export interface ScenarioTemplate {
  id: string;
  label: string;
  description: string;
  mode: "outcome" | "narrative" | "combined";
  condition: Condition | null;
  narrative_packs: string[];
  audience_scope: string[];
  report_tier: "quick" | "analyst" | "executive";
}

export interface PackInfo {
  pack_type: string;
  entity_key: string | null;
  version: number;
  description: string;
}

export type JobStatus =
  | "queued"
  | "outcome_running"
  | "outcome_done"
  | "narrative_running"
  | "synthesizing"
  | "done"
  | "failed";

export interface SelectionState {
  edition: string;
  mode: "outcome" | "narrative" | "combined";
  condition: Condition | null;
  narrative_packs: string[];
  audience_scope: string[];
  report_tier: "quick" | "analyst" | "executive";
}

export interface Confidence {
  data_quality?: string;
  effective_runs?: number;
  requested_runs?: number;
  acceptance_rate?: number;
  thin_sample?: boolean;
  rating_coverage?: number;
  flags?: Flag[];
}

export interface Flag {
  level: "high" | "medium" | "low";
  type: string;
  message: string;
}

export interface ComparativeResult {
  _winner: string;
  _winner_prob: number;
  narratives: NarrativeCluster[];
  sentiment: SentimentData;
  sample_posts: SyntheticPost[];
  turning_points: TurningPoint[];
  error?: string;
}

export interface SimulationResult {
  run_id: string;
  status: JobStatus;
  data_version?: string | null;
  mode?: string | null;
  condition?: Condition | null;
  outcome: OutcomeResult | null;
  narrative: NarrativeResult | null;
  comparative: ComparativeResult[] | null;
  confidence: Confidence | null;
  disclaimer: string;
}

export interface FinalPath {
  final: string;
  probability: number;
}

/** stage_probs[stage][team] = P(team reaches at least `stage` | condition). */
export type StageProbs = Record<string, Record<string, number>>;

export interface OutcomeResult {
  champion_probs: Record<string, number>;
  finalist_probs?: Record<string, number>;
  stage_probs?: StageProbs;
  top_paths?: FinalPath[];
  effective_runs: number;
  confidence: Confidence;
}

export interface NarrativeResult {
  narratives: NarrativeCluster[];
  sentiment: SentimentData;
  sample_posts: SyntheticPost[];
  turning_points: TurningPoint[];
  confidence: Record<string, unknown>;
  metadata: Record<string, unknown>;
}

export interface NarrativeCluster {
  cluster_id: string;
  label: string;
  dominance: number;
  agent_count: number;
}

export interface SentimentData {
  overall: number[];
  timestamps: string[];
}

export interface SyntheticPost {
  post_id: string;
  agent_id: string;
  content: string;
  round: number;
  synthetic: boolean;
}

export interface TurningPoint {
  round: number;
  direction: "up" | "down";
  magnitude: number;
  sentiment: number;
}

export interface ChampionEntry {
  team: string;
  probability: number;
  change?: number;
}

// ===== Single-Match Types =====

export interface MatchRequest {
  home_fifa_code: string;
  away_fifa_code: string;
  n_runs: number;
  neutral: boolean;
  goal_line?: number | null;
  seed?: number | null;
}

export interface TeamInfo {
  fifa_code: string;
  name: string;
  confederation: string;
  elo: number;
}

export interface GoalLineQuery {
  line: number;
  prob_over: number;
  prob_under: number;
}

export interface ScorelineEntry {
  scoreline: string;
  probability: number;
}

export interface MatchResult {
  home_team: TeamInfo;
  away_team: TeamInfo;
  win_home: number;
  draw: number;
  win_away: number;
  expected_goals_home: number;
  expected_goals_away: number;
  expected_total: number;
  mean_simulated_home: number;
  mean_simulated_away: number;
  total_goals_distribution: Record<string, number>;
  over_under: Record<string, number>;
  both_teams_score: number;
  top_scorelines: ScorelineEntry[];
  goal_line_query: GoalLineQuery | null;
  confidence: MatchConfidence;
  data_version: Record<string, unknown> | null;
}

export interface MatchConfidence {
  n_runs: number;
  rating_coverage: number;
  form_applied: boolean;
}
