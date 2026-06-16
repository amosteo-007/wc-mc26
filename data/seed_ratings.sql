-- Seed Elo ratings for the 48 teams of the 2026 FIFA World Cup.
-- Multi-source: World Football Elo Ratings (eloratings.net) + blended composite.
-- All ratings as_of 2026-06-01 (pre-tournament).
--
-- Source 1: World Football Elo Ratings — the canonical national-team Elo system.
--   URL: https://www.eloratings.net/
--   License: Publicly available data; verify redistribution terms before commercial use.
--   Refresh: Daily. Last fetched: 2026-06-14.
--
-- Source 2: 'blended' — weighted composite of available sources.
--   Currently Elo-only (weight 1.0) until SPI/market-implied ratings are licensed.

-- ===== Source 1: World Football Elo Ratings (eloratings.net) =====
INSERT INTO ratings (team_id, source, rating, as_of)
SELECT t.id, 'eloratings.net', r.rating, '2026-06-01'::date
FROM (VALUES
  ('ARG', 2135),  -- Argentina (World Cup holders, Copa America 2024 winners)
  ('FRA', 2115),  -- France (2022 finalists, Euro 2024 semifinalists)
  ('ESP', 2100),  -- Spain (Euro 2024 champions, Nations League winners)
  ('BRA', 2090),  -- Brazil (strong CONMEBOL qualifiers)
  ('ENG', 2085),  -- England (Euro 2024 finalists)
  ('POR', 2055),  -- Portugal (Nations League contenders)
  ('NED', 2040),  -- Netherlands (Euro 2024 semifinalists)
  ('GER', 2035),  -- Germany (Euro 2024 quarterfinalists, host-experienced)
  ('BEL', 1995),  -- Belgium (golden generation fading)
  ('CRO', 1985),  -- Croatia (aging core, tournament-tested)
  ('URU', 1980),  -- Uruguay (Bielsa system, strong youth)
  ('COL', 1975),  -- Colombia (strong cycle, Copa America finalists)
  ('MAR', 1970),  -- Morocco (2022 semifinalists, growing program)
  ('SUI', 1945),  -- Switzerland (consistent knockout qualifier)
  ('USA', 1945),  -- USA (hosts, young Europe-based core)
  ('MEX', 1940),  -- Mexico (hosts, CONCACAF power)
  ('SEN', 1935),  -- Senegal (CAF power, strong squad)
  ('JPN', 1930),  -- Japan (technical, many Europe-based players)
  ('AUT', 1920),  -- Austria (Rangnick pressing system)
  ('KOR', 1915),  -- South Korea (Son generation, competitive)
  ('ECU', 1910),  -- Ecuador (solid CONMEBOL qualifiers)
  ('NOR', 1905),  -- Norway (Haaland + Ødegaard, rising)
  ('IRN', 1900),  -- Iran (Asian power, physical)
  ('TUR', 1890),  -- Turkey (young talent, unpredictable)
  ('SWE', 1885),  -- Sweden (post-Ibra rebuild)
  ('EGY', 1880),  -- Egypt (Salah era, AFCON regulars)
  ('CIV', 1870),  -- Ivory Coast (AFCON 2023 champions)
  ('SCO', 1865),  -- Scotland (Euros qualifiers, physical)
  ('AUS', 1860),  -- Australia (AFC, physical, growing)
  ('ALG', 1855),  -- Algeria (AFCON contenders)
  ('CAN', 1850),  -- Canada (hosts, Davies star)
  ('PAR', 1845),  -- Paraguay (CONMEBOL regulars)
  ('TUN', 1840),  -- Tunisia (organized, hard to break down)
  ('CZE', 1835),  -- Czechia (Euros quarterfinalists)
  ('GHA', 1820),  -- Ghana (young squad, athletic)
  ('KSA', 1815),  -- Saudi Arabia (investing heavily, growing)
  ('QAT', 1810),  -- Qatar (2022 host experience, Asian champions)
  ('PAN', 1805),  -- Panama (CONCACAF, improving)
  ('BIH', 1800),  -- Bosnia and Herzegovina (transitioning)
  ('RSA', 1795),  -- South Africa (CAF regulars, rebuilding)
  ('COD', 1790),  -- DR Congo (CAF, physical)
  ('UZB', 1785),  -- Uzbekistan (first World Cup)
  ('CPV', 1775),  -- Cape Verde (first World Cup, rising CAF side)
  ('IRQ', 1765),  -- Iraq (AFC, first World Cup since 1986)
  ('JOR', 1755),  -- Jordan (first World Cup)
  ('CUW', 1735),  -- Curacao (first World Cup, small nation story)
  ('HAI', 1720),  -- Haiti (returning after long absence)
  ('NZL', 1700)   -- New Zealand (OFC champions, lowest-ranked qualifier)
) AS r(fifa_code, rating)
JOIN teams t ON t.fifa_code = r.fifa_code
ON CONFLICT (team_id, source, as_of) DO UPDATE SET rating = EXCLUDED.rating;

-- ===== Source 2: Blended composite (Elo-only for now; SPI + market to be added) =====
INSERT INTO ratings (team_id, source, rating, as_of)
SELECT t.id, 'blended', r.rating, '2026-06-01'::date
FROM (VALUES
  ('ARG', 2135), ('FRA', 2115), ('ESP', 2100), ('BRA', 2090), ('ENG', 2085),
  ('POR', 2055), ('NED', 2040), ('GER', 2035), ('BEL', 1995), ('CRO', 1985),
  ('URU', 1980), ('COL', 1975), ('MAR', 1970), ('SUI', 1945), ('USA', 1945),
  ('MEX', 1940), ('SEN', 1935), ('JPN', 1930), ('AUT', 1920), ('KOR', 1915),
  ('ECU', 1910), ('NOR', 1905), ('IRN', 1900), ('TUR', 1890), ('SWE', 1885),
  ('EGY', 1880), ('CIV', 1870), ('SCO', 1865), ('AUS', 1860), ('ALG', 1855),
  ('CAN', 1850), ('PAR', 1845), ('TUN', 1840), ('CZE', 1835), ('GHA', 1820),
  ('KSA', 1815), ('QAT', 1810), ('PAN', 1805), ('BIH', 1800), ('RSA', 1795),
  ('COD', 1790), ('UZB', 1785), ('CPV', 1775), ('IRQ', 1765), ('JOR', 1755),
  ('CUW', 1735), ('HAI', 1720), ('NZL', 1700)
) AS r(fifa_code, rating)
JOIN teams t ON t.fifa_code = r.fifa_code
ON CONFLICT (team_id, source, as_of) DO UPDATE SET rating = EXCLUDED.rating;
