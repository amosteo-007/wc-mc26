-- Live 2026 FIFA World Cup results — group stage in progress (as of 2026-06-16).
-- Matchday 1 complete for Groups A-F; Groups G-L have not yet kicked off.
-- Source: live standings (CBS Sports / LiveScore), verified 2026-06-16.
-- Knockout stage is therefore entirely TBD.

INSERT INTO wc_results (stage, group_name, matchday, home_code, away_code, home_goals, away_goals, played_on) VALUES
-- Group A
('group', 'A', 1, 'MEX', 'RSA', 2, 0, '2026-06-11'),
('group', 'A', 1, 'KOR', 'CZE', 2, 1, '2026-06-12'),
-- Group B
('group', 'B', 1, 'CAN', 'BIH', 1, 1, '2026-06-12'),
('group', 'B', 1, 'QAT', 'SUI', 1, 1, '2026-06-13'),
-- Group C
('group', 'C', 1, 'BRA', 'MAR', 1, 1, '2026-06-13'),
('group', 'C', 1, 'SCO', 'HAI', 1, 0, '2026-06-13'),
-- Group D
('group', 'D', 1, 'USA', 'PAR', 4, 1, '2026-06-12'),
('group', 'D', 1, 'AUS', 'TUR', 2, 0, '2026-06-13'),
-- Group E
('group', 'E', 1, 'GER', 'CUW', 7, 1, '2026-06-13'),
('group', 'E', 1, 'CIV', 'ECU', 1, 0, '2026-06-14'),
-- Group F
('group', 'F', 1, 'NED', 'JPN', 2, 2, '2026-06-14'),
('group', 'F', 1, 'SWE', 'TUN', 5, 1, '2026-06-14');
-- Groups G-L: no matches played yet (knockout bracket all TBD).
