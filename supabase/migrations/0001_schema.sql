-- ============================================================
-- The India Directory — schema migration
-- Creates: states, officials, mlas, mps, mps_coverage, change_log
-- ============================================================

create table if not exists states (
  id            text primary key,               -- 'union', 'telangana', 'andhra_pradesh', 'karnataka'
  name          text not null,                   -- 'Andhra Pradesh'
  level         text not null check (level in ('union','state')),
  assembly_name text,                            -- e.g. '16th Andhra Pradesh Legislative Assembly (2024–2029)'
  source_url    text,
  created_at    timestamptz not null default now()
);

comment on table states is 'One row per government tier tracked: the Union and each state.';

-- ------------------------------------------------------------
-- officials: Prime Minister / Chief Ministers / cabinet ministers
-- ------------------------------------------------------------
create table if not exists officials (
  id             bigserial primary key,
  state_id       text not null references states(id) on delete cascade,
  role_type      text not null check (role_type in ('chief','minister')),
  role_title     text not null,                  -- 'Prime Minister of India' or the portfolio, e.g. 'Home Affairs; Cooperation'
  name           text not null,
  seat           text,                            -- constituency / Rajya Sabha seat, ministers only
  note           text,
  source_url     text,
  last_checked   date,
  confidence     text check (confidence in ('high','medium','low')),
  display_order  int not null default 0,
  created_at     timestamptz not null default now(),
  updated_at     timestamptz not null default now()
);

comment on table officials is 'Chief executives (role_type=chief: PM/CM) and their key cabinet ministers (role_type=minister).';

create index if not exists officials_state_idx on officials(state_id);
create unique index if not exists officials_one_chief_per_state on officials(state_id) where role_type = 'chief';

-- ------------------------------------------------------------
-- mlas: every constituency's sitting Member of the Legislative Assembly
-- ------------------------------------------------------------
create table if not exists mlas (
  id             bigserial primary key,
  state_id       text not null references states(id) on delete cascade,
  seat_no        int not null,                    -- constituency number within the state
  constituency   text not null,
  reservation    text check (reservation in ('SC','ST', null)),
  name           text not null,
  party          text,
  note           text,                             -- by-election / defection / death notes
  source_url     text,
  last_checked   date,
  confidence     text check (confidence in ('high','medium','low')),
  created_at     timestamptz not null default now(),
  updated_at     timestamptz not null default now(),
  unique (state_id, seat_no)
);

comment on table mlas is 'Every seat of the tracked state legislative assemblies, one row per constituency.';

create index if not exists mlas_state_idx on mlas(state_id);
create index if not exists mlas_constituency_idx on mlas(constituency);
create index if not exists mlas_party_idx on mlas(party);

-- ------------------------------------------------------------
-- mps: Lok Sabha (Union Parliament) seats. Distinct from mlas because MPs
-- are elected from national constituencies, not tied to a single state's
-- assembly structure -- state_id here is which state elects each seat, but
-- the seat itself belongs to the Union government.
-- ------------------------------------------------------------
create table if not exists mps (
  id             bigserial primary key,
  state_id       text not null references states(id) on delete cascade,
  seat_no        int not null,                    -- constituency number within the state
  constituency   text not null,
  reservation    text check (reservation in ('SC','ST', null)),
  name           text not null,
  party          text,
  note           text,
  source_url     text,
  last_checked   date,
  confidence     text check (confidence in ('high','medium','low')),
  created_at     timestamptz not null default now(),
  updated_at     timestamptz not null default now(),
  unique (state_id, seat_no)
);

comment on table mps is 'Lok Sabha (Union Parliament) seats, state by state. Coverage is partial -- see mps_coverage.';

create index if not exists mps_state_idx on mps(state_id);
create index if not exists mps_constituency_idx on mps(constituency);
create index if not exists mps_party_idx on mps(party);

-- ------------------------------------------------------------
-- mps_coverage: tracks which states/UTs have been added to `mps` and which
-- are still pending, with the source used/suggested for each. Mirrors
-- data/mps-pending.json so the pipeline and any reviewer can see progress
-- without cross-referencing the JSON files.
-- ------------------------------------------------------------
create table if not exists mps_coverage (
  state_name      text primary key,
  seats_total     int not null,
  seats_collected int not null default 0,
  status          text not null default 'pending' check (status in ('pending','in_progress','done')),
  source_url      text,
  notes           text,
  updated_at      timestamptz not null default now()
);

comment on table mps_coverage is 'Progress tracker for MP data collection across all 36 states/UTs.';

-- ------------------------------------------------------------
-- change_log: audit trail written by the daily pipeline (scripts/update.py)
-- Mirrors the PR-review workflow: every proposed change is logged here,
-- whether or not it was auto-applied (officials) or held for review (mlas/mps).
-- ------------------------------------------------------------
create table if not exists change_log (
  id             bigserial primary key,
  table_name     text not null check (table_name in ('officials','mlas','mps')),
  record_id      bigint,                          -- id in the target table, null if the record didn't exist yet
  state_id       text references states(id),
  field_changed  text not null,
  old_value      text,
  new_value      text,
  source_url     text,
  confidence     text check (confidence in ('high','medium','low')),
  auto_applied   boolean not null default false,   -- true for officials (auto-committed), false for mlas/mps (PR review)
  reviewed       boolean not null default false,   -- set true once a human approves a change
  created_at     timestamptz not null default now()
);

comment on table change_log is 'Every change the daily pipeline finds, whether auto-applied or awaiting review.';

create index if not exists change_log_table_idx on change_log(table_name, reviewed);
create index if not exists change_log_state_idx on change_log(state_id);

-- ------------------------------------------------------------
-- updated_at triggers
-- ------------------------------------------------------------
create or replace function set_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

drop trigger if exists officials_set_updated_at on officials;
create trigger officials_set_updated_at
  before update on officials
  for each row execute function set_updated_at();

drop trigger if exists mlas_set_updated_at on mlas;
create trigger mlas_set_updated_at
  before update on mlas
  for each row execute function set_updated_at();

drop trigger if exists mps_set_updated_at on mps;
create trigger mps_set_updated_at
  before update on mps
  for each row execute function set_updated_at();

-- ------------------------------------------------------------
-- Row Level Security: public read-only, writes via service role only
-- (the daily pipeline authenticates with the service role key)
-- ------------------------------------------------------------
alter table states enable row level security;
alter table officials enable row level security;
alter table mlas enable row level security;
alter table mps enable row level security;
alter table mps_coverage enable row level security;
alter table change_log enable row level security;

drop policy if exists "public read states" on states;
create policy "public read states" on states for select using (true);

drop policy if exists "public read officials" on officials;
create policy "public read officials" on officials for select using (true);

drop policy if exists "public read mlas" on mlas;
create policy "public read mlas" on mlas for select using (true);

drop policy if exists "public read mps" on mps;
create policy "public read mps" on mps for select using (true);

drop policy if exists "public read mps_coverage" on mps_coverage;
create policy "public read mps_coverage" on mps_coverage for select using (true);

-- change_log is not public: it's an internal audit trail for the pipeline/reviewers
drop policy if exists "service role only on change_log" on change_log;
create policy "service role only on change_log" on change_log for all using (auth.role() = 'service_role');
