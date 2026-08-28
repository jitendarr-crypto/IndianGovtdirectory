#!/usr/bin/env python3
"""
Generates index.html (Union Government + landing) and one HTML page per
state (telangana.html, punjab.html, etc.) from shared templates, so the
site doesn't load all 14 states' data on every single page view.

Run this after adding a new state: add its data files, add one entry to
ALL_STATES in shared.js AND to the STATES list below, then re-run this
script to regenerate every page (all pages share the same nav, so every
page needs regenerating when a state is added -- this script does that
in one shot rather than by hand).
"""
import os

OUT = os.path.dirname(os.path.abspath(__file__))

CLOUDFLARE_SNIPPET = '''<!-- Cloudflare Web Analytics -->
<script type='module' src='https://static.cloudflareinsights.com/beacon.min.js' data-cf-beacon='{"token": "d601291611ac48d78a86afa57a8ce8e2"}'></script>
<!-- End Cloudflare Web Analytics -->'''

HEAD = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} — The India Directory</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600;9..144,700&family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<link rel="stylesheet" href="shared.css">
</head>
<body>
'''

MASTHEAD = '''<div class="masthead">
  <div class="masthead-inner">
    <div class="brand">
      <div class="seal">
        <svg viewBox="0 0 24 24" fill="none" stroke="#C9A75C" stroke-width="1.2">
          <circle cx="12" cy="12" r="9"/>
          <g>
            <line x1="12" y1="3" x2="12" y2="21"/>
            <line x1="3" y1="12" x2="21" y2="12"/>
            <line x1="5.5" y1="5.5" x2="18.5" y2="18.5"/>
            <line x1="18.5" y1="5.5" x2="5.5" y2="18.5"/>
          </g>
          <circle cx="12" cy="12" r="2" fill="#C9A75C" stroke="none"/>
        </svg>
      </div>
      <div class="brand-text">
        <p class="eyebrow">A civic reference, gazette style</p>
        <h1>The India Directory</h1>
      </div>
    </div>
    <div class="masthead-meta">
      VOL. I · UNION &amp; STATE EDITION<br>
      <span id="last-verified-badge">LOADING LIVE DATA…</span><br>
      NEXT IN QUEUE: FULL STATE ROLLOUT
    </div>
  </div>
  <hr class="masthead-rule">
  <nav class="tier-nav" id="nav-placeholder"></nav>
</div>

<div class="wrap">
'''

FOOTER = '''</div>

<footer>
  THE INDIA DIRECTORY — an unofficial civic reference. Not affiliated with the Government of India or any state government. Verify anything election‑ or appointment‑sensitive against the official source linked inline before relying on it.
  <br><br>
  Found an error, or want to suggest a state? <a href="contact.html" style="color:var(--gold-soft);border-bottom:1px solid rgba(201,167,92,.4);text-decoration:none;">Contact us</a>.
</footer>

''' + CLOUDFLARE_SNIPPET + '''
</body>
</html>
'''

SEARCH_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="7"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>'


def state_section(key, label, custom=None):
    """Builds one state's <section>. `custom`, if given, is a dict with
    hand-written text (tier_head_p, leadership_caveat, mla_desc, mla_caveat)
    for the 3 states that had richer hand-written copy before this refactor.
    Everything else is left for shared.js's bootStatePage() to fill in from
    the data itself at load time (same as the 11 states already did)."""
    custom = custom or {}
    tier_head_p = custom.get("tier_head_p", "Chief Minister, key cabinet portfolios, and every MLA — loading…")
    leadership_caveat = custom.get("leadership_caveat", "")
    mla_desc = custom.get("mla_desc", "")
    mla_caveat = custom.get("mla_caveat", "")

    return f'''  <section class="tier active" id="{key}">
    <div class="tier-head">
      <div>
        <h2>Government of {label}</h2>
        <p>{tier_head_p}</p>
      </div>
      <div class="as-of">AS REPORTED · AUG 2026</div>
    </div>
    <hr class="gazette">

    <div class="chief-strip">
      <div class="chief-photo-seal" id="{key}-photo">--</div>
      <div class="chief-info">
        <div class="role">Chief Minister of {label}</div>
        <h3 id="{key}-chief-name">…</h3>
        <div class="sub" id="{key}-chief-note"></div>
      </div>
    </div>

    <h3 style="font-family:'Fraunces',serif;font-size:20px;color:var(--navy-deep);margin:0 0 16px;">Council of Ministers — key portfolios</h3>
    <div class="office-grid" id="{key}-grid"></div>

    <div class="caveat" id="{key}-leadership-caveat" style="margin-bottom:44px;">{leadership_caveat}</div>

    <h3 style="font-family:'Fraunces',serif;font-size:20px;color:var(--navy-deep);margin:0 0 6px;">Constituencies &amp; MLAs</h3>
    <p style="color:var(--ink-soft);font-size:13.5px;margin:0 0 20px;max-width:640px;" id="{key}-mla-desc">{mla_desc}</p>

    <div class="districts-toolbar">
      <div class="search-box">
        {SEARCH_ICON}
        <input type="text" id="mla-search-{key}" placeholder="Search a constituency or MLA…">
      </div>
      <div class="count-tag" id="mla-count-{key}">loading…</div>
    </div>

    <div class="table-scroll">
    <table class="districts">
      <thead>
        <tr>
          <th>No.</th>
          <th>Constituency</th>
          <th>MLA</th>
          <th>Party</th>
          <th>Notes</th>
        </tr>
      </thead>
      <tbody id="mlas-body-{key}"></tbody>
    </table>
    </div>

    <div class="caveat" id="{key}-mla-caveat">{mla_caveat}</div>
  </section>
'''


# ============================================================
# Per-state custom copy for the 3 states built by hand before this
# refactor existed. Every other state uses shared.js's auto-generated
# caveat text (computed from the data itself at load time).
# ============================================================
CUSTOM_COPY = {
    "telangana": {
        "tier_head_p": "Chief Minister, key cabinet portfolios, and every MLA in Telangana's 119-seat Legislative Assembly.",
        "leadership_caveat": 'Source: <a class="verify-link" href="https://www.telangana.gov.in/government/council-of-ministers/" target="_blank" rel="noopener">telangana.gov.in — Council of Ministers</a>. The cabinet has grown since its Dec 2023 formation (several ministers inducted through 2025–26); this list reflects the officially published portfolio table.',
        "mla_desc": "All 119 constituencies of the 3rd Telangana Legislative Assembly (2023–2028), with their sitting MLA and party.",
        "mla_caveat": 'Source: <a class="verify-link" href="https://en.wikipedia.org/wiki/3rd_Telangana_Assembly" target="_blank" rel="noopener">3rd Telangana Assembly</a> — includes by-election winners and party defections recorded since the 2023 election. MLAs are elected for a five-year term, so this list is far more stable than an appointed-official roster, but always worth a quick check on anything election- or defection-sensitive.',
    },
    "andhra": {
        "tier_head_p": "Chief Minister, key cabinet portfolios, and every MLA in Andhra Pradesh's 175-seat Legislative Assembly.",
        "leadership_caveat": "Source: portfolio table compiled from sarkaritel.com's Andhra Pradesh Council of Ministers page (last updated 17 Jul 2026) and contemporaneous reporting. Naidu's fourth ministry took office 12 June 2024 with 24 ministers plus the CM; several portfolios have shifted since.",
        "mla_desc": "All 175 constituencies of the 16th Andhra Pradesh Legislative Assembly (2024–2029), with their sitting MLA and party.",
        "mla_caveat": 'Source: <a class="verify-link" href="https://en.wikipedia.org/wiki/16th_Andhra_Pradesh_Assembly" target="_blank" rel="noopener">16th Andhra Pradesh Assembly</a> — TDP holds a majority (135 seats) with NDA allies JSP and BJP; rows without an explicit party tag in the source table are TDP. MLAs serve five-year terms, so this is far more stable than an appointed-official roster, but still worth a quick check on anything election-sensitive.',
    },
    "karnataka": {
        "tier_head_p": "Chief Minister, key cabinet portfolios, and every MLA in Karnataka's 224-seat Legislative Assembly.",
        "leadership_caveat": "Source: portfolio allocations reported June–August 2026 (Business Today, Deccan Herald, Wikipedia's Shivakumar ministry page). The cabinet was initially sworn in with 14 members on 3 June 2026 and expanded on 3 August 2026; some portfolios were revised again on 12 August 2026.",
        "mla_desc": "All 224 constituencies of the 16th Karnataka Legislative Assembly (2023–2028), with their sitting MLA and party.",
        "mla_caveat": 'Source: <a class="verify-link" href="https://en.wikipedia.org/wiki/16th_Karnataka_Assembly" target="_blank" rel="noopener">16th Karnataka Assembly</a> — includes by-election winners, deaths in office, and party switches recorded since the 2023 election, including Hiriyur, currently vacant after D. Sudhakar\'s death in May 2026. MLAs serve five-year terms, so this is far more stable than an appointed-official roster, but still worth a quick check on anything election-sensitive.',
    },
}

# key, label -- must match ALL_STATES in shared.js exactly
STATES = [
    ("telangana", "Telangana"),
    ("andhra", "Andhra Pradesh"),
    ("karnataka", "Karnataka"),
    ("uttar_pradesh", "Uttar Pradesh"),
    ("maharashtra", "Maharashtra"),
    ("tamil_nadu", "Tamil Nadu"),
    ("kerala", "Kerala"),
    ("bihar", "Bihar"),
    ("madhya_pradesh", "Madhya Pradesh"),
    ("rajasthan", "Rajasthan"),
    ("gujarat", "Gujarat"),
    ("odisha", "Odisha"),
    ("assam", "Assam"),
    ("punjab", "Punjab"),
]


def write(path, content):
    with open(os.path.join(OUT, path), "w", encoding="utf-8") as f:
        f.write(content)
    print("wrote", path)


def generate_state_page(key, label):
    html = HEAD.format(title=label)
    html += MASTHEAD
    html += state_section(key, label, CUSTOM_COPY.get(key))
    html += FOOTER
    html += f'''<script src="shared.js"></script>
<script>
buildNav("{key}");
bootStatePage("{key}", "{label}");
</script>
</body>
</html>
'''
    write(f"{key}.html", html)


def generate_index():
    html = HEAD.format(title="Union Government")
    html += MASTHEAD
    html += '''  <section class="tier active" id="union">
    <div class="tier-head">
      <div>
        <h2>Union Government of India</h2>
        <p>The Prime Minister and the key cabinet portfolios of the Union Council of Ministers, Third Modi Ministry.</p>
      </div>
      <div class="as-of">AS REPORTED · AUG 2026</div>
    </div>
    <hr class="gazette">

    <div class="chief-strip">
      <div class="chief-photo-seal" id="pm-photo">NM</div>
      <div class="chief-info">
        <div class="role">Prime Minister of India</div>
        <h3 id="union-chief-name">Narendra Modi</h3>
        <div class="sub" id="union-chief-note">Also holds: Personnel, Public Grievances &amp; Pensions · Department of Atomic Energy · Department of Space</div>
      </div>
    </div>

    <div class="office-grid" id="union-grid"></div>

    <div class="caveat">
      <strong>On photos.</strong> The PM's photo above is his official portrait from pmindia.gov.in. For everyone else, sourcing a stable, hotlink-safe photo URL for each minister isn't something I can do reliably at scale — official sites and Wikipedia don't expose plain image links the way this tool can fetch — so the seal shows initials instead of risking a broken or mismatched photo. Happy to keep filling these in a few at a time if useful.
    </div>

    <div class="caveat">
      <strong>On this list.</strong> This covers the Prime Minister and the senior cabinet portfolios most relevant to a general directory — Home, Finance, Defence, External Affairs, and similar. It is not the full 70‑plus member Council of Ministers. Portfolios shift with reshuffles — Pralhad Joshi, for instance, took over Education from Dharmendra Pradhan on 25 July 2026 following the NEET‑UG controversy. For the authoritative, current list, see the <a class="verify-link" href="https://www.pmindia.gov.in/en/news_updates/portfolios-of-the-union-council-of-ministers-2/" target="_blank" rel="noopener">Portfolios of the Union Council of Ministers</a> on pmindia.gov.in.
    </div>

    <h3 style="font-family:'Fraunces',serif;font-size:20px;color:var(--navy-deep);margin:44px 0 6px;">Members of Parliament (Lok Sabha)</h3>
    <p style="color:var(--ink-soft);font-size:13.5px;margin:0 0 20px;max-width:640px;">All 543 Lok Sabha seats are elected from every state and union territory. Coverage here is in progress — built out state by state, same as the state assemblies below.</p>

    <div class="districts-toolbar">
      <div class="search-box">
        ''' + SEARCH_ICON + '''
        <input type="text" id="mp-search" placeholder="Search a constituency, MP, or state…">
      </div>
      <div class="count-tag" id="mp-count">loading…</div>
    </div>

    <div class="table-scroll">
    <table class="districts">
      <thead>
        <tr>
          <th>State</th>
          <th>Constituency</th>
          <th>MP</th>
          <th>Party</th>
        </tr>
      </thead>
      <tbody id="mps-body"></tbody>
    </table>
    </div>

    <div class="caveat">
      <strong>128 of 543 seats covered so far</strong> — Uttar Pradesh (80) and Maharashtra (48), both sourced from Wikipedia's official 2024 election-results tables and cross-checked against vote margins. The remaining 415 seats across 34 states and union territories are queued in <code>data/mps-pending.json</code> with a source link for each — every large-scale MP data source turned out to have its own quirks (broken pagination, blocked robots.txt, inconsistent table markup), so each state needs individual verification rather than one bulk pull. See the README for how this gets extended.
    </div>
  </section>

  <div class="extend">
    <div>
      <h3>Built to grow, state by state</h3>
      <p id="extend-copy">Loading…</p>
    </div>
    <div class="state-pills" id="extend-pills"></div>
  </div>
'''
    html += FOOTER
    html += '''<script src="shared.js"></script>
<script>
buildNav("union");
renderBuiltToGrow();

async function boot(){
  try {
    const [union, mpsUP, mpsMH] = await Promise.all([
      fetchJson("union-leadership.json"),
      fetchJson("mps-uttar_pradesh.json"),
      fetchJson("mps-maharashtra.json"),
    ]);

    renderOfficeGrid("union-grid", union.ministers);
    renderChiefInfo("union", union.chief);
    renderChiefPhoto("pm-photo", union.chief.name, "https://www.pmindia.gov.in/wp-content/uploads/2025/12/02.jpg");

    renderMps([{data: mpsUP, slug: "uttar_pradesh"}, {data: mpsMH, slug: "maharashtra"}]);
    document.getElementById("mp-search").addEventListener("input", (e)=> renderMps([{data: mpsUP, slug: "uttar_pradesh"}, {data: mpsMH, slug: "maharashtra"}], e.target.value));

    const allChecked = [union.chief.last_checked, ...union.ministers.map(m=>m.last_checked)].filter(Boolean).sort();
    document.getElementById("last-verified-badge").textContent = `LEADERSHIP VERIFIED ${allChecked[allChecked.length - 1] || "unknown"}`;
  } catch (err) {
    console.error(err);
    document.getElementById("last-verified-badge").textContent = "LIVE DATA UNAVAILABLE (open via a server, not file://)";
  }
}
boot();
</script>
</body>
</html>
'''
    write("index.html", html)


if __name__ == "__main__":
    generate_index()
    for key, label in STATES:
        generate_state_page(key, label)
    print(f"\nGenerated index.html + {len(STATES)} state pages.")
