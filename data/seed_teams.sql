-- Seed data: the 48 teams of the 2026 FIFA World Cup, per the official final
-- draw (Washington, DC — 5 December 2025). Verified against ESPN/NBC Sports.
-- Source of group composition: FIFA final draw.

INSERT INTO teams (fifa_code, name, confederation) VALUES
-- Group A
('MEX', 'Mexico', 'CONCACAF'),
('KOR', 'South Korea', 'AFC'),
('RSA', 'South Africa', 'CAF'),
('CZE', 'Czechia', 'UEFA'),
-- Group B
('CAN', 'Canada', 'CONCACAF'),
('SUI', 'Switzerland', 'UEFA'),
('QAT', 'Qatar', 'AFC'),
('BIH', 'Bosnia and Herzegovina', 'UEFA'),
-- Group C
('BRA', 'Brazil', 'CONMEBOL'),
('MAR', 'Morocco', 'CAF'),
('SCO', 'Scotland', 'UEFA'),
('HAI', 'Haiti', 'CONCACAF'),
-- Group D
('USA', 'United States', 'CONCACAF'),
('PAR', 'Paraguay', 'CONMEBOL'),
('AUS', 'Australia', 'AFC'),
('TUR', 'Turkey', 'UEFA'),
-- Group E
('GER', 'Germany', 'UEFA'),
('ECU', 'Ecuador', 'CONMEBOL'),
('CIV', 'Ivory Coast', 'CAF'),
('CUW', 'Curacao', 'CONCACAF'),
-- Group F
('NED', 'Netherlands', 'UEFA'),
('JPN', 'Japan', 'AFC'),
('TUN', 'Tunisia', 'CAF'),
('SWE', 'Sweden', 'UEFA'),
-- Group G
('BEL', 'Belgium', 'UEFA'),
('IRN', 'Iran', 'AFC'),
('EGY', 'Egypt', 'CAF'),
('NZL', 'New Zealand', 'OFC'),
-- Group H
('ESP', 'Spain', 'UEFA'),
('URU', 'Uruguay', 'CONMEBOL'),
('KSA', 'Saudi Arabia', 'AFC'),
('CPV', 'Cape Verde', 'CAF'),
-- Group I
('FRA', 'France', 'UEFA'),
('SEN', 'Senegal', 'CAF'),
('NOR', 'Norway', 'UEFA'),
('IRQ', 'Iraq', 'AFC'),
-- Group J
('ARG', 'Argentina', 'CONMEBOL'),
('AUT', 'Austria', 'UEFA'),
('ALG', 'Algeria', 'CAF'),
('JOR', 'Jordan', 'AFC'),
-- Group K
('POR', 'Portugal', 'UEFA'),
('COL', 'Colombia', 'CONMEBOL'),
('UZB', 'Uzbekistan', 'AFC'),
('COD', 'DR Congo', 'CAF'),
-- Group L
('ENG', 'England', 'UEFA'),
('CRO', 'Croatia', 'UEFA'),
('PAN', 'Panama', 'CONCACAF'),
('GHA', 'Ghana', 'CAF')
ON CONFLICT (fifa_code) DO NOTHING;
