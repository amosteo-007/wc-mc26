-- Tournament format spec for WC2026
-- 48 teams, 12 groups of 4, top 2 + 8 best third-placed teams advance to Round of 32
-- 104 matches total (72 group stage + 32 knockout)
--
-- Groups source: FIFA Final Draw (Washington DC, 5 December 2025)
-- Bracket structure: FIFA official 48-team format (12 groups of 4 -> R32 -> R16 -> QF -> SF -> Final)
-- Host venues: 16 cities across USA (11), Mexico (3), Canada (2)
--
-- CRITICAL: The groups array below MUST match data/seed_teams.sql exactly.
-- The Monte Carlo simulator reads both; if out of sync, it runs on wrong data.

INSERT INTO tournament_format (edition, spec) VALUES ('WC2026', '{
  "edition": "WC2026",
  "total_teams": 48,
  "num_groups": 12,
  "teams_per_group": 4,
  "group_matches": 72,
  "knockout_matches": 32,
  "total_matches": 104,

  "group_stage": {
    "format": "round_robin",
    "points": {"win": 3, "draw": 1, "loss": 0},
    "tiebreakers": [
      "points",
      "goal_difference",
      "goals_scored",
      "head_to_head_points",
      "head_to_head_goal_difference",
      "head_to_head_goals_scored",
      "fair_play_points",
      "drawing_of_lots"
    ],
    "advancement": {
      "group_winners": 12,
      "group_runners_up": 12,
      "best_third_placed": 8
    },
    "best_thirds_ranking": [
      "points",
      "goal_difference",
      "goals_scored",
      "fair_play_points",
      "drawing_of_lots"
    ]
  },

  "knockout_stage": {
    "rounds": ["R32", "R16", "QF", "SF", "3rd_place", "Final"],
    "format": "single_elimination",
    "extra_time": true,
    "penalties": true,
    "third_place_match": true
  },

  "groups": [
    {"group": "A", "teams": ["MEX", "KOR", "RSA", "CZE"]},
    {"group": "B", "teams": ["CAN", "SUI", "QAT", "BIH"]},
    {"group": "C", "teams": ["BRA", "MAR", "SCO", "HAI"]},
    {"group": "D", "teams": ["USA", "PAR", "AUS", "TUR"]},
    {"group": "E", "teams": ["GER", "ECU", "CIV", "CUW"]},
    {"group": "F", "teams": ["NED", "JPN", "TUN", "SWE"]},
    {"group": "G", "teams": ["BEL", "IRN", "EGY", "NZL"]},
    {"group": "H", "teams": ["ESP", "URU", "KSA", "CPV"]},
    {"group": "I", "teams": ["FRA", "SEN", "NOR", "IRQ"]},
    {"group": "J", "teams": ["ARG", "AUT", "ALG", "JOR"]},
    {"group": "K", "teams": ["POR", "COL", "UZB", "COD"]},
    {"group": "L", "teams": ["ENG", "CRO", "PAN", "GHA"]}
  ],

  "knockout_bracket": {
    "R32": [
      {"match": 1,  "home": "1A", "away": "3C/D/E",    "slot": "best_third_1", "desc": "1A vs 3C/D/E"},
      {"match": 2,  "home": "2C", "away": "2D",         "slot": null,           "desc": "2C vs 2D"},
      {"match": 3,  "home": "1E", "away": "3A/B/C",    "slot": "best_third_2", "desc": "1E vs 3A/B/C"},
      {"match": 4,  "home": "1G", "away": "3A/E/F",    "slot": "best_third_3", "desc": "1G vs 3A/E/F"},
      {"match": 5,  "home": "1C", "away": "3A/B/F",    "slot": "best_third_4", "desc": "1C vs 3A/B/F"},
      {"match": 6,  "home": "2A", "away": "2B",         "slot": null,           "desc": "2A vs 2B"},
      {"match": 7,  "home": "1I", "away": "3C/D/F",    "slot": "best_third_5", "desc": "1I vs 3C/D/F"},
      {"match": 8,  "home": "1K", "away": "3B/E/F",    "slot": "best_third_6", "desc": "1K vs 3B/E/F"},
      {"match": 9,  "home": "1B", "away": "3E/F/G",    "slot": "best_third_7", "desc": "1B vs 3E/F/G"},
      {"match": 10, "home": "2E", "away": "2F",         "slot": null,           "desc": "2E vs 2F"},
      {"match": 11, "home": "1F", "away": "2G",         "slot": null,           "desc": "1F vs 2G"},
      {"match": 12, "home": "1J", "away": "2I",         "slot": null,           "desc": "1J vs 2I"},
      {"match": 13, "home": "1H", "away": "3D/E/F",    "slot": "best_third_8", "desc": "1H vs 3D/E/F"},
      {"match": 14, "home": "2K", "away": "2L",         "slot": null,           "desc": "2K vs 2L"},
      {"match": 15, "home": "1D", "away": "2J",         "slot": null,           "desc": "1D vs 2J"},
      {"match": 16, "home": "1L", "away": "2H",         "slot": null,           "desc": "1L vs 2H"}
    ],

    "R16": [
      {"match": 1, "home": "W32-1", "away": "W32-2", "desc": "Winner R32-1 vs Winner R32-2"},
      {"match": 2, "home": "W32-3", "away": "W32-4", "desc": "Winner R32-3 vs Winner R32-4"},
      {"match": 3, "home": "W32-5", "away": "W32-6", "desc": "Winner R32-5 vs Winner R32-6"},
      {"match": 4, "home": "W32-7", "away": "W32-8", "desc": "Winner R32-7 vs Winner R32-8"},
      {"match": 5, "home": "W32-9", "away": "W32-10", "desc": "Winner R32-9 vs Winner R32-10"},
      {"match": 6, "home": "W32-11", "away": "W32-12", "desc": "Winner R32-11 vs Winner R32-12"},
      {"match": 7, "home": "W32-13", "away": "W32-14", "desc": "Winner R32-13 vs Winner R32-14"},
      {"match": 8, "home": "W32-15", "away": "W32-16", "desc": "Winner R32-15 vs Winner R32-16"}
    ],

    "QF": [
      {"match": 1, "home": "W16-1", "away": "W16-2", "desc": "Winner R16-1 vs Winner R16-2"},
      {"match": 2, "home": "W16-3", "away": "W16-4", "desc": "Winner R16-3 vs Winner R16-4"},
      {"match": 3, "home": "W16-5", "away": "W16-6", "desc": "Winner R16-5 vs Winner R16-6"},
      {"match": 4, "home": "W16-7", "away": "W16-8", "desc": "Winner R16-7 vs Winner R16-8"}
    ],

    "SF": [
      {"match": 1, "home": "WQF-1", "away": "WQF-2", "desc": "Winner QF-1 vs Winner QF-2"},
      {"match": 2, "home": "WQF-3", "away": "WQF-4", "desc": "Winner QF-3 vs Winner QF-4"}
    ],

    "3rd_place": {
      "home": "LSF-1", "away": "LSF-2", "desc": "Loser SF-1 vs Loser SF-2"
    },

    "Final": {
      "home": "WSF-1", "away": "WSF-2", "desc": "Winner SF-1 vs Winner SF-2"
    }
  },

  "host_venues": {
    "usa": [
      {"city": "Seattle",         "state": "WA", "stadium": "Lumen Field"},
      {"city": "San Francisco",   "state": "CA", "stadium": "Levi''s Stadium"},
      {"city": "Los Angeles",     "state": "CA", "stadium": "SoFi Stadium"},
      {"city": "Kansas City",     "state": "MO", "stadium": "Arrowhead Stadium"},
      {"city": "Dallas",          "state": "TX", "stadium": "AT&T Stadium"},
      {"city": "Houston",         "state": "TX", "stadium": "NRG Stadium"},
      {"city": "Atlanta",         "state": "GA", "stadium": "Mercedes-Benz Stadium"},
      {"city": "Chicago",         "state": "IL", "stadium": "Soldier Field"},
      {"city": "Philadelphia",    "state": "PA", "stadium": "Lincoln Financial Field"},
      {"city": "Boston",          "state": "MA", "stadium": "Gillette Stadium"},
      {"city": "New York / New Jersey", "state": "NJ", "stadium": "MetLife Stadium"}
    ],
    "mexico": [
      {"city": "Mexico City",   "stadium": "Estadio Azteca"},
      {"city": "Guadalajara",   "stadium": "Estadio Akron"},
      {"city": "Monterrey",     "stadium": "Estadio BBVA"}
    ],
    "canada": [
      {"city": "Vancouver", "province": "BC", "stadium": "BC Place"},
      {"city": "Toronto",   "province": "ON", "stadium": "BMO Field"}
    ]
  }
}'::jsonb)
ON CONFLICT (edition) DO UPDATE SET spec = EXCLUDED.spec;
