-- Postgres schema: structured outcome data + run bookkeeping.
-- The narrative *graph* lives in Neo4j; this DB holds tabular data and run state.

-- ============ Outcome-engine reference data ============
CREATE TABLE teams (
  id          SERIAL PRIMARY KEY,
  fifa_code   TEXT UNIQUE NOT NULL,        -- e.g. 'BRA'
  name        TEXT NOT NULL,
  confederation TEXT                       -- CONMEBOL, UEFA, ...
);

CREATE TABLE ratings (                     -- baseline strength; many sources/dates
  team_id     INT REFERENCES teams(id),
  source      TEXT NOT NULL,               -- 'eloratings.net', 'spi', 'blended'
  rating      DOUBLE PRECISION NOT NULL,
  as_of       DATE NOT NULL,
  PRIMARY KEY (team_id, source, as_of)
);

CREATE TABLE matches_history (             -- historical + qualifier results
  id          BIGSERIAL PRIMARY KEY,
  match_date  DATE NOT NULL,
  home_id     INT REFERENCES teams(id),
  away_id     INT REFERENCES teams(id),
  home_goals  INT,
  away_goals  INT,
  competition TEXT,                        -- 'friendly','wc_qualifier','wc_finals'...
  neutral     BOOLEAN DEFAULT FALSE
);
CREATE INDEX idx_hist_date ON matches_history(match_date);

CREATE TABLE tournament_format (           -- 2026: 48 teams / 12 groups / 104 matches
  edition     TEXT PRIMARY KEY,            -- 'WC2026'
  spec        JSONB NOT NULL               -- groups, advancement, bracket, tiebreaks
);

CREATE TABLE wc_results (                   -- live 2026 World Cup match results
  id          BIGSERIAL PRIMARY KEY,
  edition     TEXT NOT NULL DEFAULT 'WC2026',
  stage       TEXT NOT NULL,               -- 'group','R32','R16','QF','SF','final'
  group_name  TEXT,                        -- 'A'..'L' for group-stage matches
  matchday    INT,                         -- 1..3 in group stage
  home_code   TEXT NOT NULL,               -- fifa_code (not id; loaded pre-team-join)
  away_code   TEXT NOT NULL,
  home_goals  INT NOT NULL,
  away_goals  INT NOT NULL,
  played_on   DATE,
  -- A given pairing is played at most once in the tournament, so this makes the
  -- daily fetcher's upsert idempotent (ON CONFLICT updates the score in place).
  UNIQUE (edition, stage, home_code, away_code)
);
CREATE INDEX idx_wc_results_group ON wc_results(edition, group_name);

-- ============ Run bookkeeping ============
CREATE TABLE sim_runs (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  mode        TEXT NOT NULL,               -- 'outcome'|'narrative'|'combined'
  condition   JSONB,                       -- preset condition as MC constraint
  packs       JSONB,                       -- selected narrative packs
  audience    JSONB,                       -- audience lenses
  tier        TEXT NOT NULL,               -- 'quick'|'analyst'|'executive'
  n_runs      INT NOT NULL,                -- 10k..100k by tier
  data_version TEXT NOT NULL DEFAULT 'unknown',  -- snapshot date + pack versions (reproducibility)
  status      TEXT NOT NULL DEFAULT 'queued',
  created_at  TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE outcome_results (
  run_id        UUID REFERENCES sim_runs(id),
  champion_probs JSONB,                    -- {team_code: p}
  finalist_probs JSONB,
  top_paths      JSONB,                    -- most frequent bracket paths
  upset_freq     JSONB,
  confidence     JSONB,                    -- data-quality notes
  PRIMARY KEY (run_id)
);

CREATE TABLE world_specs (                 -- GPT-authored control file for narrative
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id      UUID REFERENCES sim_runs(id),
  spec        JSONB NOT NULL               -- outcome summary, packs, horizon, metrics
);

CREATE TABLE narrative_results (
  run_id        UUID REFERENCES sim_runs(id),
  world_spec_id UUID REFERENCES world_specs(id),
  narratives    JSONB,                     -- dominant clusters
  sentiment     JSONB,                     -- by audience/time
  sponsor_matrix JSONB,
  sample_posts  JSONB,
  turning_points JSONB,
  confidence     JSONB,
  PRIMARY KEY (run_id, world_spec_id)
);

-- Prebuilt narrative context packs (authored, versioned content).
CREATE TABLE context_packs (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  pack_type   TEXT NOT NULL,               -- team|sponsor|fan|media|political|platform
  entity_key  TEXT,                        -- e.g. 'BRA' for team packs
  version     INT NOT NULL DEFAULT 1,
  payload     JSONB NOT NULL
);
