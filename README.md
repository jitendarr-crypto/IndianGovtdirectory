# The India Directory — self-updating civic reference

A directory of the Union Government and select state governments (currently
Telangana, Andhra Pradesh, Karnataka) with a daily automated check for
changes in office — Chief Minister, key ministers, and every sitting MLA.

## How it works

```
data/*.json              ← the actual "database" (git-versioned JSON)
scripts/update.py        ← asks Claude (with web search) to verify each entry
.github/workflows/       ← runs update.py daily via GitHub Actions
index.html               ← the site, fetches data/*.json at load time
```

Every night, GitHub Actions runs `scripts/update.py`, which asks Claude to
check each tracked person against the live web. Two different trust levels:

- **Leadership** (Chief Minister / PM / cabinet ministers) — low volatility.
  Confirmed changes are committed straight to `main`.
- **MLAs** (all 518 sitting members across the three states) — MLAs serve
  five-year terms so this list is naturally stable, but by-elections,
  deaths, and party defections do happen and are politically sensitive, so
  any detected change opens a **pull request** instead of pushing directly,
  so you can glance at the source before it goes live.

## Database (Supabase)

The `supabase/migrations/` folder has the full schema and seed data, tested
end-to-end against a real Postgres instance before being included here:

```
supabase/migrations/
  0001_schema.sql              ← tables: states, officials, mlas, change_log
  0002_seed_states.sql         ← the 4 tracked states
  0003_seed_officials.sql      ← 48 rows: every PM/CM + cabinet minister
  0004_seed_mlas_telangana.sql ← 119 rows
  0005_seed_mlas_andhra.sql    ← 175 rows
  0006_seed_mlas_karnataka.sql ← 224 rows
```

**Schema shape:**
- `states` — the 4 tracked governments (union, telangana, andhra_pradesh, karnataka)
- `officials` — chief executives and key ministers (`role_type` = `chief` or `minister`)
- `mlas` — one row per constituency across all three states (518 total)
- `change_log` — audit trail the daily pipeline writes to, whether a change was auto-applied (officials) or held for review (mlas)

Row Level Security is on for all four tables: `states`/`officials`/`mlas` are
public read-only; `change_log` is service-role only (internal to the
pipeline/reviewers, not meant for the public site).

**To apply this to a Supabase project:**

Option A — Supabase CLI:
```bash
supabase link --project-ref <your-project-ref>
supabase db push
```

Option B — SQL Editor in the Supabase dashboard: open each file in
`supabase/migrations/` in order and run it.

Once applied, `index.html`'s `fetchJson()` calls can be pointed at Supabase's
REST API (`https://<project-ref>.supabase.co/rest/v1/mlas?state_id=eq.telangana`
etc., with the anon key) instead of the static `data/*.json` files, and
`scripts/update.py` can write directly to the database instead of the JSON
files — the `change_log` table is designed for exactly that: log every
proposed change there, auto-apply the `officials` ones, and leave the `mlas`
ones with `reviewed = false` until a human flips it to `true` (or wires up
the same GitHub PR flow against the `mlas` table instead of a JSON diff).

## Members of Parliament (Lok Sabha)

The Union Government tab now includes an MP directory — **128 of 543 seats
collected so far** (Uttar Pradesh's 80 and Maharashtra's 48), with the
remaining 34 states/UTs tracked in `data/mps-pending.json` and the
`mps_coverage` Supabase table, each with a suggested source URL.

**Why only 2 states:** every large-scale MP data source turned out to have
its own failure mode — MyNeta.info's winners list has no working URL-based
pagination past ~330 rows, the official Parliament PDF is blocked by
robots.txt, and even Wikipedia's per-state `2024 Indian general election in
<State>` results-table pages (which worked cleanly for UP and Maharashtra)
failed to extract on West Bengal due to inconsistent table markup. There's
no reliable bulk pull here — each state needs individual verification.

**To add another state:**
1. Try fetching `https://en.wikipedia.org/wiki/2024_Indian_general_election_in_<State>` —
   look for the "Constituency / Turnout / Winner / Runner-up / Margin" table.
   If it renders as empty pipes, that page's markup didn't extract; try the
   `List_of_Lok_Sabha_members_from_<State>` page instead, or a state-specific
   news source.
2. Add `data/mps-<state_slug>.json` following the shape of the existing files.
3. Add the filename to `MP_FILES` in `scripts/update.py`.
4. Remove that state from `data/mps-pending.json` and add a
   `supabase/migrations/00XX_seed_mps_<state>.sql` file (or write directly
   to Supabase).
5. Update `mps_coverage` (`status = 'done'`, `seats_collected = <n>`).

## States covered so far

| State | MLAs | Source |
|---|---|---|
| Telangana | 119 | 3rd Telangana Assembly (Wikipedia) |
| Andhra Pradesh | 175 | 16th Andhra Pradesh Assembly (Wikipedia) |
| Karnataka | 224 | 16th Karnataka Assembly (Wikipedia) |
| Uttar Pradesh | 403 | 18th Uttar Pradesh Assembly (Wikipedia) |
| Maharashtra | 288 | findeasy.in, cross-checked against MyNeta/ADR + 2 live 2026 by-elections |
| Bihar | 243 | findeasy.in, cross-checked against MyNeta/ADR + 1 live 2026 by-election |
| Tamil Nadu | 234 | findeasy.in + tnmla.in, cross-checked against Wikipedia's by-election tracker |
| Madhya Pradesh | 230 | 16th Madhya Pradesh Assembly (Wikipedia), with 2 confirmed by-elections |
| Kerala | 140 | keralaballot.in (sourced from results.eci.gov.in) — every seat cross-validated against the official party tally (12 parties, exact match) |
| Rajasthan | 200 | Rajasthan Legislative Assembly (Wikipedia), with 9 confirmed by-elections |
| Gujarat | 182 | Gujarat Legislative Assembly (Wikipedia), with 8 confirmed by-elections |
| Odisha | 147 | myneta.info + 16 individually-confirmed Wikipedia constituency pages |

**2,585 MLAs total, 11 vacant seats tracked** (Karnataka's Hiriyur, 3 in
UP, 7 in Tamil Nadu — all following confirmed deaths or resignations,
never guessed).

Tamil Nadu was the biggest political story of the batch: actor-turned
politician C. Joseph Vijay's brand-new party TVK won 108 of 234 seats in
its first-ever election (May 2026), ending 59 years of DMK/AIADMK
dominance and forming a coalition government — the state's first hung
assembly. Kerala had its own scare: an early search result claimed the
incumbent LDF won a third term, which was simply wrong — three
independent sources confirmed UDF actually won 102/140 seats, ending
LDF's 10-year run. Kerala's Wikipedia assembly table also uses merged/
rowspan cells for party, which would have silently misattributed several
seats via naive forward-fill; switching to an ECI-sourced dashboard with
an explicit party per row (and a state-wide tally that matched exactly)
avoided that. Madhya Pradesh, by contrast, was clean and stable (last
election Nov 2023) — no fresh-election chaos to untangle. Rajasthan was
similarly stable (last election Nov 2023) — 9 by-elections tracked,
including one seat (Anta) vacated by a disqualification rather than a
death or resignation, and one where I caught a wrong assumption before
it shipped: Dausa's 2024 by-election was won by Congress, not BJP, even
though 5 of the other 6 seats in that same round went to BJP — worth
checking each one rather than assuming a sweep was total. Gujarat added a
distinctive pattern: 5 of its 2024 by-elections were "resign and
rejoin BJP" cases — the same MLA who quit Congress (or, in one case,
independent status) to defect was then re-elected on a BJP ticket in
the resulting by-election for their own seat, confirmed against multiple
news sources rather than assumed from the pattern. Odisha ended a
historic 24-year Biju Janata Dal (BJD) run — Mohan Charan Majhi is the
state's first BJP Chief Minister — and hit the same MyNeta gap pattern
as Maharashtra/Bihar (16 of 147 seats missing), each confirmed
individually against a dedicated Wikipedia constituency page rather
than left blank or guessed; one of those 16 (Nuapada) also needed a
2025 by-election update after the sitting MLA died in office. West
Bengal (294 seats) remains skipped — see the note above.

## Constituency detail pages

Every constituency name in the MLA/MP tables links to `constituency.html`,
which shows a map of India with that constituency's state highlighted (plus
a pin at the state's centroid) and a detail card with the sitting
representative, party, and source.

**What this is, and isn't:** the map highlights the *state*, not the exact
constituency boundary — real constituency-level GIS boundary data (precise
polygon shapes for 2,000+ seats) isn't something reliably sourceable the
way the name/party data is, so this was scoped down deliberately rather
than faked. The map data itself is a real, modern state-boundary GeoJSON
(`data/india-states.geojson`, ~1.7MB, includes Telangana/Ladakh-era
boundaries) rendered client-side with D3 — nothing is pre-rendered or
hardcoded per state.

Links use `constituency.html?type=mla&state=<slug>&no=<seat_no>` (or
`type=mp` for the Lok Sabha table). Historical MLA data ("last 5 MLAs")
was scoped out for now — flagged as a separate future research project,
similar in size to the current-MLA rollout itself, since constituency
boundaries also changed in the 2008 delimitation.

## Contact page

`contact.html` is a form (name, email, topic, message) that emails
submissions to the site maintainer via Formspree. It was set up through
Formspree's agent-integration flow (`formspree.io/ai`) — a claim link was
generated, the site owner claimed it in their browser, and the resulting
endpoint (`https://formspree.io/f/mjybnkly`) was wired into the form's
`action`. No credentials were ever shared to set this up. Linked from the
main directory's footer.

## One-time setup

1. **Create a GitHub repo** and push everything in this folder to it.
   ```
   cd india-directory
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin https://github.com/<you>/<repo>.git
   git push -u origin main
   ```

2. **Add your Anthropic API key as a repo secret.**
   Repo → Settings → Secrets and variables → Actions → New repository secret
   - Name: `ANTHROPIC_API_KEY`
   - Value: your key from console.anthropic.com

3. **Enable GitHub Pages** so the site is actually viewable at a URL.
   Repo → Settings → Pages → Source: `Deploy from a branch` → Branch: `main` / `(root)`.
   Your site will be at `https://<you>.github.io/<repo>/`.

4. **Enable Actions** if not already on (Settings → Actions → General →
   Allow all actions). The workflow is already scheduled for 03:00 UTC daily
   and can also be run manually from the **Actions** tab
   (`Daily Government Directory Check` → `Run workflow`).

That's it — the first scheduled run will happen within 24h, or trigger it
manually to see it work immediately.

## Running it locally (to test before pushing)

```bash
cd india-directory
pip install -r scripts/requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...
python scripts/update.py          # updates data/*.json in place, prints a summary

python3 -m http.server 8000       # serve the site (fetch() needs http, not file://)
# open http://localhost:8000
```

## Reviewing an MLA-update PR

Each PR the bot opens contains the run's summary (source URLs and the
old→new name for every proposed change) in its description. If a source
looks solid, merge it. If it looks thin, edit the PR's diff directly or
close it — nothing is lost, `update.py` will re-check that constituency
again on the next run.

## Extending to another state

1. Add `data/<state>-leadership.json` and `data/<state>-mlas.json`
   following the shape of the existing files.
2. Add the filenames to `LEADERSHIP_FILES` / `MLA_FILES` in
   `scripts/update.py`.
3. Add one entry to `DYNAMIC_STATES` in `index.html`'s `<script>` block
   (e.g. `{key:"maharashtra", label:"Maharashtra"}`) — the nav button,
   section markup, and search box are all generated automatically. No
   HTML to hand-write.
4. Add a `supabase/migrations/00XX_seed_states_<state>.sql`,
   `00XX_seed_officials_<state>.sql`, and `00XX_seed_mlas_<state>.sql`
   (or write directly to Supabase).

## Known limitations

- MLA and leadership data both rely on Wikipedia's assembly pages and
  news reporting rather than a structured government API, so even daily
  automated checks are really "daily search-and-read," and will
  occasionally miss a change or need a human's judgment call in the PR.
- The checker calls the Anthropic API with web search once per state per
  category (≈7 calls/day total) — cheap, but keep an eye on usage if you
  extend to many more states.
- `index.html` must be served over HTTP (GitHub Pages, or
  `python -m http.server` locally) — opening the file directly
  (`file://...`) will fail `fetch()` due to browser CORS rules.
