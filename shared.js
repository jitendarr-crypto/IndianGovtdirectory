// ============================================================
// shared.js — common data fetching, rendering, and navigation
// logic used by every page (index.html + each state page).
// One state page = one HTML file that fetches only its own
// data, rather than every state's data loading on every page.
// ============================================================

const DATA_BASE = "data";

async function fetchJson(name){
  const res = await fetch(`${DATA_BASE}/${name}?_=${Date.now()}`);
  if(!res.ok) throw new Error(`Failed to load ${name}: ${res.status}`);
  return res.json();
}

function initials(name){
  return name.split(" ").filter(w=>/^[A-Za-z]/.test(w)).slice(0,2).map(w=>w[0]).join("").toUpperCase();
}

function stampHtml(name, photoUrl){
  const ini = initials(name);
  if (!photoUrl) return ini;
  return `<img src="${photoUrl}" alt="${name}" loading="lazy" onerror="this.parentElement.innerHTML='${ini}';this.parentElement.classList.add('no-photo');">`;
}

function renderOfficeGrid(containerId, list){
  const el = document.getElementById(containerId);
  el.innerHTML = list.map((m,i)=>`
    <div class="office-card">
      <span class="stamp">${stampHtml(m.name, m.photo)}</span>
      <span class="office-num">${String(i+1).padStart(2,'0')}</span>
      <h4>${m.name}</h4>
      <div class="portfolio">${m.portfolio}</div>
      <div class="constituency">${m.seat}</div>
    </div>
  `).join("");
}

function renderChiefPhoto(elId, name, photoUrl){
  const el = document.getElementById(elId);
  if(el) el.innerHTML = stampHtml(name, photoUrl);
}

function renderChiefInfo(prefix, chief){
  const nameEl = document.getElementById(`${prefix}-chief-name`);
  const noteEl = document.getElementById(`${prefix}-chief-note`);
  if(nameEl) nameEl.textContent = chief.name;
  if(noteEl && chief.note) noteEl.textContent = chief.note;
}

function renderMps(allMpStates, filter=""){
  const body = document.getElementById(`mps-body`);
  const f = filter.trim().toLowerCase();
  const rows = [];
  for (const {data, slug} of allMpStates) {
    for (const d of data.items) {
      rows.push({state: data.state, slug, ...d});
    }
  }
  const totalCollected = rows.length;
  const filtered = rows.filter(d =>
    d.constituency.toLowerCase().includes(f) ||
    d.name.toLowerCase().includes(f) ||
    d.state.toLowerCase().includes(f) ||
    (d.party||"").toLowerCase().includes(f)
  );
  document.getElementById("mp-count").textContent = `${filtered.length} of ${totalCollected} collected (543 total seats)`;
  body.innerHTML = filtered.map(d => `
    <tr>
      <td class="dhq">${d.state}</td>
      <td class="dname"><a class="verify-link" href="constituency.html?type=mp&state=${d.slug}&no=${d.no}">${d.constituency}</a>${d.reservation ? ` <span class="collector-tag" style="color:var(--ink-soft);">(${d.reservation})</span>` : ""}</td>
      <td class="collector-known">${d.name}</td>
      <td class="dhq">${d.party || "—"}</td>
    </tr>`).join("");
}

function renderMlas(containerPrefix, stateData, filter=""){
  const items = stateData.items;
  const body = document.getElementById(`mlas-body-${containerPrefix}`);
  const f = filter.trim().toLowerCase();
  const rows = items.filter(d => d.constituency.toLowerCase().includes(f) || d.name.toLowerCase().includes(f) || (d.party||"").toLowerCase().includes(f));
  document.getElementById(`mla-count-${containerPrefix}`).textContent = `${rows.length} of ${items.length} constituencies`;
  body.innerHTML = rows.map((d)=>{
    const cname = `<a class="verify-link" href="constituency.html?type=mla&state=${containerPrefix}&no=${d.no}">${d.constituency}</a>` + (d.reservation ? ` <span class="collector-tag" style="color:var(--ink-soft);">(${d.reservation})</span>` : "");
    return `
    <tr>
      <td class="dnum">${String(d.no).padStart(3,'0')}</td>
      <td class="dname">${cname}</td>
      <td class="collector-known">${d.name}</td>
      <td class="dhq">${d.party || "—"}</td>
      <td class="dhq" style="font-size:11.5px;">${d.note || ""}</td>
    </tr>`;
  }).join("");
}

// ---------------- STATE CONFIG (single source of truth for nav on every page) ----------------
// To add a new state: 1) add data/<key>-leadership.json + data/<key>-mlas.json,
// 2) generate its page with generate_pages.py, 3) add one entry here so every
// page's nav (built fresh by buildNav() below) knows about it. pinned:true
// gets its own tab; otherwise it lives in the "More states" dropdown.
const ALL_STATES = [
  {key:"telangana", label:"Telangana", pinned:true},
  {key:"andhra", label:"Andhra Pradesh", pinned:true},
  {key:"karnataka", label:"Karnataka", pinned:true},
  {key:"uttar_pradesh", label:"Uttar Pradesh", pinned:true},
  {key:"maharashtra", label:"Maharashtra", pinned:true},
  {key:"tamil_nadu", label:"Tamil Nadu", pinned:true},
  {key:"kerala", label:"Kerala", pinned:true},
  {key:"bihar", label:"Bihar"},
  {key:"madhya_pradesh", label:"Madhya Pradesh"},
  {key:"rajasthan", label:"Rajasthan"},
  {key:"gujarat", label:"Gujarat"},
  {key:"odisha", label:"Odisha"},
  {key:"assam", label:"Assam"},
  {key:"punjab", label:"Punjab"},
];

// All 28 states + the 3 union territories with their own legislative
// assembly (Delhi, J&K, Puducherry) = 31 total. Ordered roughly by
// assembly size so the "next up" pills on index.html stay meaningful
// as more states are added. This list plus ALL_STATES above is the
// only thing that needs updating -- the "Built to grow" section
// computes itself from these two lists.
const ALL_INDIA_ENTITIES = [
  "Uttar Pradesh","Maharashtra","Bihar","Tamil Nadu","Madhya Pradesh",
  "Karnataka","Rajasthan","Gujarat","Andhra Pradesh","Odisha","Kerala",
  "Telangana","Assam","West Bengal","Punjab","Chhattisgarh","Haryana",
  "Jharkhand","Jammu and Kashmir","Uttarakhand","Himachal Pradesh",
  "Delhi","Tripura","Meghalaya","Manipur","Nagaland","Goa",
  "Arunachal Pradesh","Puducherry","Mizoram","Sikkim",
];

// ---------------- NAV (renders into #nav-placeholder on every page) ----------------
function buildNav(currentKey){
  const pinned = ALL_STATES.filter(s => s.pinned);
  const dropdown = ALL_STATES.filter(s => !s.pinned).slice().sort((a,b) => a.label.localeCompare(b.label));

  const unionActive = currentKey === "union" ? " active" : "";
  const unionLink = `<a class="tier-btn${unionActive}" href="index.html">Union Government</a>`;

  const pinnedHtml = pinned.map(s =>
    `<a class="tier-btn${s.key===currentKey ? ' active' : ''}" href="${s.key}.html">${s.label}</a>`
  ).join("");

  const isDropdownState = dropdown.some(s => s.key === currentKey);
  const dropdownOptions = dropdown.map(s =>
    `<option value="${s.key}.html"${s.key===currentKey ? ' selected' : ''}>${s.label}</option>`
  ).join("");

  const nav = document.getElementById("nav-placeholder");
  if(!nav) return;
  nav.innerHTML = `
    <div class="tier-nav-left">
      ${unionLink}
      ${pinnedHtml}
    </div>
    <div class="state-select-wrap">
      <select id="state-select">
        <option value="" disabled${isDropdownState ? '' : ' selected'}>More states…</option>
        ${dropdownOptions}
      </select>
    </div>
  `;

  document.getElementById("state-select").addEventListener("change", (e)=>{
    if(e.target.value) window.location.href = e.target.value;
  });
}

// ---------------- "Built to grow" section (index.html only) ----------------
function renderBuiltToGrow(){
  const doneLabels = new Set(ALL_STATES.map(s => s.label));
  const remaining = ALL_INDIA_ENTITIES.filter(name => !doneLabels.has(name));

  const copy = document.getElementById("extend-copy");
  if(copy){
    copy.textContent = `This directory covers the Union Government and ${doneLabels.size} states so far. The same structure — Chief Minister, key ministers, every sitting MLA — extends cleanly to every other state and union territory.`;
  }

  const pillsEl = document.getElementById("extend-pills");
  if(pillsEl){
    const shown = remaining.slice(0, 5);
    const restCount = remaining.length - shown.length;
    let html = shown.map((name, i) => `<span class="pill${i===0 ? ' next' : ''}">${name}${i===0 ? ' — next' : ''}</span>`).join("");
    if(restCount > 0) html += `<span class="pill">+ ${restCount} more</span>`;
    pillsEl.innerHTML = html;
  }
}

// ---------------- Generic state-page boot ----------------
// Used by every state page. Auto-fills the leadership/MLA caveats from the
// data itself (source_url, assembly name, last_checked) unless the page has
// already hardcoded richer custom caveat text -- see generate_pages.py for
// which states have custom text (the first 3 built by hand) vs auto text.
async function bootStatePage(key, label){
  try {
    const [leadership, mlas] = await Promise.all([
      fetchJson(`${key}-leadership.json`),
      fetchJson(`${key}-mlas.json`),
    ]);

    renderOfficeGrid(`${key}-grid`, leadership.ministers);
    renderChiefInfo(key, leadership.chief);
    renderChiefPhoto(`${key}-photo`, leadership.chief.name, null);
    renderMlas(key, mlas);

    const headP = document.querySelector(`.tier-head p`);
    if(headP && headP.textContent.includes('loading')){
      headP.textContent = `Chief Minister, key cabinet portfolios, and every MLA in ${leadership.state}'s ${mlas.items.length}-seat Legislative Assembly.`;
    }
    const mlaDesc = document.getElementById(`${key}-mla-desc`);
    if(mlaDesc && !mlaDesc.textContent.trim()){
      mlaDesc.textContent = `All ${mlas.items.length} constituencies of the ${mlas.assembly}, with their sitting MLA and party.`;
    }
    const leadershipCaveat = document.getElementById(`${key}-leadership-caveat`);
    if(leadershipCaveat && !leadershipCaveat.textContent.trim()){
      leadershipCaveat.innerHTML = `Source: <a class="verify-link" href="${leadership.chief.source_url}" target="_blank" rel="noopener">${leadership.state} government portfolio listing</a>, as reported ${leadership.chief.last_checked}.`;
    }
    const mlaCaveat = document.getElementById(`${key}-mla-caveat`);
    if(mlaCaveat && !mlaCaveat.textContent.trim()){
      mlaCaveat.innerHTML = `Source: <a class="verify-link" href="${mlas.source_url}" target="_blank" rel="noopener">${mlas.assembly}</a>. MLAs serve five-year terms, so this is far more stable than an appointed-official roster, but by-elections, deaths, and party defections do happen — still worth a quick check on anything election-sensitive.`;
    }

    document.getElementById(`mla-search-${key}`).addEventListener("input", (e)=> renderMlas(key, mlas, e.target.value));

    const badge = document.getElementById("last-verified-badge");
    if(badge) badge.textContent = `VERIFIED ${leadership.chief.last_checked || "unknown"}`;
  } catch (err) {
    console.error(err);
    const badge = document.getElementById("last-verified-badge");
    if(badge) badge.textContent = "LIVE DATA UNAVAILABLE (open via a server, not file://)";
  }
}
