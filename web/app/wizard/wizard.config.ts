/* Wizard configuration — single source of truth for all selections */

export const EDITIONS = [
  {
    id: "WC2026",
    label: "2026 FIFA World Cup",
    format: "48 teams, 12 groups, 104 matches",
    hosts: ["USA", "Mexico", "Canada"],
  },
];

export const MODES = [
  {
    id: "outcome" as const,
    label: "Outcome Only",
    description: "Monte Carlo tournament simulation only — no narrative layer.",
  },
  {
    id: "narrative" as const,
    label: "Narrative Only",
    description: "Transfer value & football news reaction simulation around a fixed outcome.",
  },
  {
    id: "combined" as const,
    label: "Combined",
    description: "Full simulation: outcome probabilities + transfer/news market reactions.",
  },
];

export const CONDITIONS = [
  {
    id: "team_exits_group",
    label: "Team Exits in Group Stage",
    description: "A selected team fails to advance from the group stage.",
    needsTeam: true,
  },
  {
    id: "team_reaches_r16",
    label: "Team Reaches Round of 16",
    description: "A selected team reaches at least the Round of 16.",
    needsTeam: true,
  },
  {
    id: "team_reaches_qf",
    label: "Team Reaches Quarter-Final",
    description: "A selected team reaches at least the quarter-finals.",
    needsTeam: true,
  },
  {
    id: "team_reaches_sf",
    label: "Team Reaches Semi-Final",
    description: "A selected team reaches at least the semi-finals.",
    needsTeam: true,
  },
  {
    id: "team_reaches_final",
    label: "Team Reaches the Final",
    description: "A selected team reaches the final.",
    needsTeam: true,
  },
  {
    id: "team_wins",
    label: "Team Wins the World Cup",
    description: "A selected team wins the entire tournament.",
    needsTeam: true,
  },
  {
    id: "host_underperforms",
    label: "Host Nations Underperform",
    description: "All three host nations (USA, Mexico, Canada) fail to advance.",
    needsTeam: false,
  },
  {
    id: "underdog_semifinal",
    label: "Underdog Reaches Semifinal",
    description: "A team below Elo 1900 reaches the semifinals.",
    needsTeam: false,
  },
  {
    id: "penalty_final",
    label: "Final Decided by Penalties",
    description: "The World Cup final is decided by a penalty shootout.",
    needsTeam: false,
  },
  {
    id: "refereeing_controversy",
    label: "Refereeing Controversy",
    description: "A major refereeing decision significantly impacts a knockout match.",
    needsTeam: false,
  },
];

export const NARRATIVE_PACKS = [
  {
    id: "transfer_news",
    label: "Transfer & News",
    description: "Transfer rumors, player market value shifts, bidding wars, contract renewals, and breaking football news reaction.",
  },
];

export const AUDIENCE_SCOPES = [
  {
    id: "domestic_winner",
    label: "Winning Nation",
    description: "Fans and media from the tournament winner's country.",
  },
  {
    id: "rival",
    label: "Rival Nations",
    description: "Fans from traditional rival countries of key teams.",
  },
  {
    id: "neutral",
    label: "Neutral Observers",
    description: "Global football fans without strong allegiance in the outcome.",
  },
  {
    id: "sponsors",
    label: "Sponsors & Brands",
    description: "Commercial stakeholders and brand perspective.",
  },
  {
    id: "host_media",
    label: "Host Nation Media",
    description: "Media from USA, Mexico, and Canada.",
  },
  {
    id: "regional_latam",
    label: "Latin America",
    description: "Regional perspective from South and Central America.",
  },
  {
    id: "regional_eur",
    label: "Europe",
    description: "Regional perspective from European media and fans.",
  },
  {
    id: "regional_apac",
    label: "Asia-Pacific",
    description: "Regional perspective from AFC region.",
  },
  {
    id: "regional_mena",
    label: "Middle East & Africa",
    description: "Regional perspective from MENA and CAF regions.",
  },
];

export const REPORT_TIERS = [
  {
    id: "quick" as const,
    label: "Quick Scan",
    description: "10k simulations, 50 agents, 12 rounds — ~30 seconds",
    estimatedLatency: "~30s",
    estimatedCost: "$",
  },
  {
    id: "analyst" as const,
    label: "Analyst",
    description: "50k simulations, 200 agents, 24 rounds — ~3 minutes",
    estimatedLatency: "~3m",
    estimatedCost: "$$",
  },
  {
    id: "executive" as const,
    label: "Executive",
    description: "100k simulations, 500 agents, 40 rounds — ~8 minutes",
    estimatedLatency: "~8m",
    estimatedCost: "$$$",
  },
];

// Fallback only — the wizard fetches the live field from GET /teams at runtime.
// Kept in sync with data/seed_teams.sql (the real WC2026 48-team field).
export const TEAMS: Array<{ fifa_code: string; name: string; confederation: string }> = [
  { fifa_code: "MEX", name: "Mexico", confederation: "CONCACAF" },
  { fifa_code: "KOR", name: "South Korea", confederation: "AFC" },
  { fifa_code: "RSA", name: "South Africa", confederation: "CAF" },
  { fifa_code: "CZE", name: "Czechia", confederation: "UEFA" },
  { fifa_code: "CAN", name: "Canada", confederation: "CONCACAF" },
  { fifa_code: "SUI", name: "Switzerland", confederation: "UEFA" },
  { fifa_code: "QAT", name: "Qatar", confederation: "AFC" },
  { fifa_code: "BIH", name: "Bosnia and Herzegovina", confederation: "UEFA" },
  { fifa_code: "BRA", name: "Brazil", confederation: "CONMEBOL" },
  { fifa_code: "MAR", name: "Morocco", confederation: "CAF" },
  { fifa_code: "SCO", name: "Scotland", confederation: "UEFA" },
  { fifa_code: "HAI", name: "Haiti", confederation: "CONCACAF" },
  { fifa_code: "USA", name: "United States", confederation: "CONCACAF" },
  { fifa_code: "PAR", name: "Paraguay", confederation: "CONMEBOL" },
  { fifa_code: "AUS", name: "Australia", confederation: "AFC" },
  { fifa_code: "TUR", name: "Turkey", confederation: "UEFA" },
  { fifa_code: "GER", name: "Germany", confederation: "UEFA" },
  { fifa_code: "ECU", name: "Ecuador", confederation: "CONMEBOL" },
  { fifa_code: "CIV", name: "Ivory Coast", confederation: "CAF" },
  { fifa_code: "CUW", name: "Curacao", confederation: "CONCACAF" },
  { fifa_code: "NED", name: "Netherlands", confederation: "UEFA" },
  { fifa_code: "JPN", name: "Japan", confederation: "AFC" },
  { fifa_code: "TUN", name: "Tunisia", confederation: "CAF" },
  { fifa_code: "SWE", name: "Sweden", confederation: "UEFA" },
  { fifa_code: "BEL", name: "Belgium", confederation: "UEFA" },
  { fifa_code: "IRN", name: "Iran", confederation: "AFC" },
  { fifa_code: "EGY", name: "Egypt", confederation: "CAF" },
  { fifa_code: "NZL", name: "New Zealand", confederation: "OFC" },
  { fifa_code: "ESP", name: "Spain", confederation: "UEFA" },
  { fifa_code: "URU", name: "Uruguay", confederation: "CONMEBOL" },
  { fifa_code: "KSA", name: "Saudi Arabia", confederation: "AFC" },
  { fifa_code: "CPV", name: "Cape Verde", confederation: "CAF" },
  { fifa_code: "FRA", name: "France", confederation: "UEFA" },
  { fifa_code: "SEN", name: "Senegal", confederation: "CAF" },
  { fifa_code: "NOR", name: "Norway", confederation: "UEFA" },
  { fifa_code: "IRQ", name: "Iraq", confederation: "AFC" },
  { fifa_code: "ARG", name: "Argentina", confederation: "CONMEBOL" },
  { fifa_code: "AUT", name: "Austria", confederation: "UEFA" },
  { fifa_code: "ALG", name: "Algeria", confederation: "CAF" },
  { fifa_code: "JOR", name: "Jordan", confederation: "AFC" },
  { fifa_code: "POR", name: "Portugal", confederation: "UEFA" },
  { fifa_code: "COL", name: "Colombia", confederation: "CONMEBOL" },
  { fifa_code: "UZB", name: "Uzbekistan", confederation: "AFC" },
  { fifa_code: "COD", name: "DR Congo", confederation: "CAF" },
  { fifa_code: "ENG", name: "England", confederation: "UEFA" },
  { fifa_code: "CRO", name: "Croatia", confederation: "UEFA" },
  { fifa_code: "PAN", name: "Panama", confederation: "CONCACAF" },
  { fifa_code: "GHA", name: "Ghana", confederation: "CAF" },
];

export const MATCH_PRESETS = [
  {
    id: "arg_bra",
    label: "Argentina vs Brazil",
    home: "ARG",
    away: "BRA",
    description: "South American superclasico",
  },
  {
    id: "eng_fra",
    label: "England vs France",
    home: "ENG",
    away: "FRA",
    description: "European heavyweights",
  },
  {
    id: "usa_mex",
    label: "USA vs Mexico",
    home: "USA",
    away: "MEX",
    description: "CONCACAF rivalry — host nation clash",
  },
  {
    id: "ger_esp",
    label: "Germany vs Spain",
    home: "GER",
    away: "ESP",
    description: "Recent champions collide",
  },
  {
    id: "irn_nzl",
    label: "Iran vs New Zealand",
    home: "IRN",
    away: "NZL",
    description: "Goal-line scenario testing",
  },
];
