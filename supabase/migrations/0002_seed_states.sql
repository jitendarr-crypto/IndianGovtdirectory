-- ============================================================
-- Seed: states
-- ============================================================

insert into states (id, name, level, assembly_name, source_url) values
  ('union', 'India (Union Government)', 'union', NULL, 'https://www.pmindia.gov.in/en/news_updates/portfolios-of-the-union-council-of-ministers-2/'),
  ('telangana', 'Telangana', 'state', '3rd Telangana Legislative Assembly (2023–2028)', 'https://en.wikipedia.org/wiki/3rd_Telangana_Assembly'),
  ('andhra_pradesh', 'Andhra Pradesh', 'state', '16th Andhra Pradesh Legislative Assembly (2024–2029)', 'https://en.wikipedia.org/wiki/16th_Andhra_Pradesh_Assembly'),
  ('karnataka', 'Karnataka', 'state', '16th Karnataka Legislative Assembly (2023–2028)', 'https://en.wikipedia.org/wiki/16th_Karnataka_Assembly')
on conflict (id) do update set name = excluded.name, assembly_name = excluded.assembly_name, source_url = excluded.source_url;
