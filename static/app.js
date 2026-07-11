/* ── city picker ───────────────────────────────────────────────────────── */
let allCities = [];

function buildCityPicker(gridId, allBtn, clearBtn, countId) {
  const grid  = document.getElementById(gridId);
  const count = document.getElementById(countId);

  function updateCount() {
    const on = grid.querySelectorAll(".city-tag.on").length;
    count.textContent = on === allCities.length ? "All cities selected"
      : on === 0 ? "No cities selected (will search all)"
      : `${on} of ${allCities.length} selected`;
  }

  allCities.forEach(c => {
    const tag = document.createElement("span");
    tag.className = "city-tag on";
    tag.dataset.id = c.id;
    tag.textContent = c.label;
    tag.addEventListener("click", () => {
      tag.classList.toggle("on");
      updateCount();
    });
    grid.appendChild(tag);
  });
  updateCount();

  document.getElementById(allBtn).addEventListener("click", () => {
    grid.querySelectorAll(".city-tag").forEach(t => t.classList.add("on"));
    updateCount();
  });
  document.getElementById(clearBtn).addEventListener("click", () => {
    grid.querySelectorAll(".city-tag").forEach(t => t.classList.remove("on"));
    updateCount();
  });

  return () => [...grid.querySelectorAll(".city-tag.on")].map(t => t.dataset.id);
}

let getFlCities, getGrabCities;

async function initCityPickers() {
  const r = await fetch("/api/cities");
  allCities = await r.json();
  getFlCities   = buildCityPicker("fl-city-grid",   "fl-all-cities",   "fl-clear-cities",   "fl-city-count");
  getGrabCities = buildCityPicker("grab-city-grid", "grab-all-cities", "grab-clear-cities", "grab-city-count");
}
initCityPickers();

/* ── utils ─────────────────────────────────────────────────────────────── */
function $(sel, ctx = document) { return ctx.querySelector(sel); }
function $$(sel, ctx = document) { return [...ctx.querySelectorAll(sel)]; }

function toast(msg) {
  const t = $("#toast");
  t.textContent = msg;
  t.classList.add("show");
  setTimeout(() => t.classList.remove("show"), 2500);
}

function copyText(text) {
  navigator.clipboard.writeText(text).then(() => toast("Copied!"));
}

/* ── tabs ──────────────────────────────────────────────────────────────── */
$$(".tab-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    $$(".tab-btn").forEach(b => b.classList.remove("active"));
    $$(".tab-panel").forEach(p => p.classList.remove("active"));
    btn.classList.add("active");
    $(`#${btn.dataset.tab}`).classList.add("active");
  });
});

/* ── SSE helper ────────────────────────────────────────────────────────── */
function streamSSE(url, onData) {
  const es = new EventSource(url);
  es.onmessage = e => {
    const d = JSON.parse(e.data);
    onData(d);
    if (d.done || d.error) es.close();
  };
  es.onerror = () => { onData({ error: "Connection error" }); es.close(); };
  return es;
}

/* ══════════════════════════════════════════════════════════════════════════
   FIND LEADS
══════════════════════════════════════════════════════════════════════════ */
let flUrls = [];

$("#fl-search-btn").addEventListener("click", () => {
  const kw = $("#fl-keyword").value.trim();
  if (!kw) { toast("Enter a keyword first."); return; }

  flUrls = [];
  $("#fl-results").innerHTML = "";
  $("#fl-count").textContent = "";
  $("#fl-save-btn").style.display = "none";
  $("#fl-status").textContent = "Scraping leads across cities… please wait";
  $("#fl-search-btn").disabled = true;

  const params = new URLSearchParams({
    keyword: kw,
    by_title:    $("#fl-by-title").checked,
    posted_today: $("#fl-today").checked,
  });
  (getFlCities ? getFlCities() : []).forEach(c => params.append("cities", c));

  streamSSE(`/api/find-leads?${params}`, d => {
    if (d.status) { $("#fl-status").textContent = d.status; return; }
    if (d.error)  { $("#fl-status").textContent = "Error: " + d.error; }
    if (d.done) {
      flUrls = d.urls;
      renderUrlList("#fl-results", d.urls);
      $("#fl-count").textContent = `Count: ${d.urls.length}`;
      $("#fl-status").textContent = "Done.";
      $("#fl-save-btn").style.display = d.urls.length ? "" : "none";
    }
    $("#fl-search-btn").disabled = false;
  });
});

function renderUrlList(selector, urls) {
  const ul = $(selector);
  ul.innerHTML = urls.map(u =>
    u.startsWith("http")
      ? `<li><a href="${u}" target="_blank">${u}</a></li>`
      : `<li>${u}</li>`
  ).join("");
}

$("#fl-save-btn").addEventListener("click", () => {
  const blob = new Blob([flUrls.join("\n")], { type: "text/plain" });
  const a = Object.assign(document.createElement("a"), {
    href: URL.createObjectURL(blob), download: "leads.txt"
  });
  a.click();
});

/* ══════════════════════════════════════════════════════════════════════════
   BUSINESS FINDER
══════════════════════════════════════════════════════════════════════════ */
let bfResults = [];
let bfSelected = null;

$("#bf-search-btn").addEventListener("click", () => {
  const keyword  = $("#bf-keyword").value.trim();
  const location = $("#bf-location").value.trim();
  if (!keyword || !location) { toast("Enter business type and location."); return; }

  const sources = [];
  if ($("#bf-osm").checked)   sources.push("OpenStreetMap");
  if ($("#bf-gmaps").checked) sources.push("Google Maps");
  if ($("#bf-yelp").checked)  sources.push("Yelp");
  if (!sources.length) { toast("Select at least one source."); return; }

  const gmapsKey = $("#bf-gmaps-key").value.trim();
  const yelpKey  = $("#bf-yelp-key").value.trim();
  if (sources.includes("Google Maps") && !gmapsKey) {
    toast("Paste your Google Maps API key."); return;
  }
  if (sources.includes("Yelp") && !yelpKey) {
    toast("Paste your Yelp API key."); return;
  }

  bfResults = [];
  bfSelected = null;
  $("#bf-tbody").innerHTML = "";
  $("#bf-pitch").value = "";
  $("#bf-status").textContent = `Searching…`;
  $("#bf-search-btn").disabled = true;

  const params = new URLSearchParams({ keyword, location, gmaps_key: gmapsKey, yelp_key: yelpKey });
  sources.forEach(s => params.append("sources", s));

  streamSSE(`/api/business-finder?${params}`, d => {
    if (d.status) { $("#bf-status").textContent = d.status; return; }
    if (d.error)  { $("#bf-status").textContent = "Error: " + d.error; }
    if (d.done) {
      bfResults = d.results;
      applyBfFilter();
      const total    = d.results.length;
      const problems = d.results.filter(b => b.issues.length).length;
      $("#bf-status").textContent = `${total} businesses found | ${problems} have issues`;
    }
    $("#bf-search-btn").disabled = false;
  });
});

function applyBfFilter() {
  const active = $$(".bf-filter:checked").map(cb => cb.value);
  const shown = active.length
    ? bfResults.filter(b => active.some(f => b.issues.join(" ").toLowerCase().includes(f)))
    : bfResults;
  renderBfTable(shown);
}

$$(".bf-filter").forEach(cb => cb.addEventListener("change", applyBfFilter));

function renderBfTable(rows) {
  const tbody = $("#bf-tbody");
  tbody.innerHTML = rows.map((b, i) => {
    const hasIssues = b.issues.length > 0;
    const issueText = hasIssues ? b.issues.join(", ") : "✓ No obvious issues";
    const websiteCell = b.website
      ? `<a href="${b.website}" target="_blank">${b.website}</a>`
      : "(none)";
    return `<tr data-idx="${i}">
      <td>${b.name}</td>
      <td>${b.source}</td>
      <td>${b.phone || "—"}</td>
      <td>${b.rating ?? "N/A"}</td>
      <td class="${hasIssues ? "problem" : "ok"}">${issueText}</td>
      <td>${websiteCell}</td>
    </tr>`;
  }).join("");

  $$("tr[data-idx]", tbody).forEach(tr => {
    tr.addEventListener("click", () => {
      $$("tr.selected", tbody).forEach(r => r.classList.remove("selected"));
      tr.classList.add("selected");
      const idx = parseInt(tr.dataset.idx);
      bfSelected = rows[idx];
      $("#bf-pitch").value = bfSelected.pitch || "";
    });
  });
}

$("#bf-copy-pitch").addEventListener("click", () => {
  const t = $("#bf-pitch").value.trim();
  if (t) copyText(t); else toast("Select a business first.");
});

$("#bf-open-website").addEventListener("click", () => {
  if (bfSelected?.website) window.open(bfSelected.website, "_blank");
  else toast("No website for selected business.");
});

$("#bf-export-csv").addEventListener("click", () => {
  if (!bfResults.length) { toast("Run a search first."); return; }
  const rows = [["Business","Source","Phone","Rating","Website","Issues","Pitch"]];
  bfResults.forEach(b => rows.push([
    b.name, b.source, b.phone, b.rating ?? "", b.website,
    b.issues.join("; "), b.pitch
  ]));
  const csv = rows.map(r => r.map(c => `"${String(c).replace(/"/g,'""')}"`).join(",")).join("\n");
  const a = Object.assign(document.createElement("a"), {
    href: URL.createObjectURL(new Blob([csv], { type: "text/csv" })),
    download: "businesses.csv"
  });
  a.click();
});

/* ══════════════════════════════════════════════════════════════════════════
   MESSAGE GENERATOR
══════════════════════════════════════════════════════════════════════════ */
$$(".msg-btns .btn").forEach(btn => {
  btn.addEventListener("click", async () => {
    const pool = btn.dataset.pool;
    const r = await fetch(`/api/message/random?pool=${pool}`);
    const d = await r.json();
    $("#msg-text").value = d.message || "";
  });
});

$("#msg-copy").addEventListener("click", () => {
  const t = $("#msg-text").value.trim();
  if (t) copyText(t); else toast("Generate a message first.");
});

$("#msg-save").addEventListener("click", async () => {
  const text = $("#msg-text").value.trim();
  if (!text) { toast("Nothing to save."); return; }
  await fetch("/api/message/save", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text })
  });
  toast("Custom message saved!");
});

/* ══════════════════════════════════════════════════════════════════════════
   GIG / PAY / PROMO SITES
══════════════════════════════════════════════════════════════════════════ */
async function loadSites() {
  const r = await fetch("/api/sites");
  const d = await r.json();

  function renderButtons(containerId, sites, cls) {
    const el = $(containerId);
    el.innerHTML = sites.map(([name, url]) =>
      `<a href="${url}" target="_blank"><button class="btn ${cls}">${name}</button></a>`
    ).join("");
  }

  renderButtons("#gig-btns",   d.gig,   "green");
  renderButtons("#pay-btns",   d.pay,   "blue");
  renderButtons("#promo-btns", d.promo, "green");
}
loadSites();

/* ══════════════════════════════════════════════════════════════════════════
   CLIENTS
══════════════════════════════════════════════════════════════════════════ */
async function loadClients() {
  const r = await fetch("/api/clients");
  const clients = await r.json();
  const tbody = $("#cl-tbody");
  tbody.innerHTML = clients.map((c, i) => `
    <tr>
      <td>${i + 1}</td>
      <td>${c[0] || "—"}</td>
      <td>${c[1] || "—"}</td>
      <td>${c[2] || "—"}</td>
      <td><button class="btn red sm" data-idx="${i}">Delete</button></td>
    </tr>
  `).join("");

  $$("button[data-idx]", tbody).forEach(btn => {
    btn.addEventListener("click", async () => {
      await fetch(`/api/clients/${btn.dataset.idx}`, { method: "DELETE" });
      loadClients();
    });
  });
}
loadClients();

$("#cl-save").addEventListener("click", async () => {
  const name  = $("#cl-name").value.trim();
  const email = $("#cl-email").value.trim();
  const phone = $("#cl-phone").value.trim();
  if (!name && !email && !phone) { toast("Fill in at least one field."); return; }
  await fetch("/api/clients", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, email, phone })
  });
  $("#cl-name").value = "";
  $("#cl-email").value = "";
  $("#cl-phone").value = "";
  loadClients();
  toast("Client saved!");
});

$("#cl-export").addEventListener("click", () => {
  window.location = "/api/clients/export";
});

/* ══════════════════════════════════════════════════════════════════════════
   GRAB LEADS
══════════════════════════════════════════════════════════════════════════ */
$("#grab-btn").addEventListener("click", () => {
  $("#grab-results").innerHTML = "";
  $("#grab-count").textContent = "";
  $("#grab-status").textContent = "Searching… please wait";
  $("#grab-btn").disabled = true;

  const grabParams = new URLSearchParams();
  (getGrabCities ? getGrabCities() : []).forEach(c => grabParams.append("cities", c));

  streamSSE(`/api/grab-leads?${grabParams}`, d => {
    if (d.status) { $("#grab-status").textContent = d.status; return; }
    if (d.error)  { $("#grab-status").textContent = "Error: " + d.error; }
    if (d.done) {
      renderUrlList("#grab-results", d.urls);
      $("#grab-count").textContent = `${d.urls.length} leads found (query: "${d.query}")`;
      $("#grab-status").textContent = "Done.";
    }
    $("#grab-btn").disabled = false;
  });
});

/* ══════════════════════════════════════════════════════════════════════════
   URL TAB
══════════════════════════════════════════════════════════════════════════ */
async function loadSavedUrl() {
  const r = await fetch("/api/data");
  const d = await r.json();
  if (d.custom_url) $("#url-input").value = d.custom_url;
}
loadSavedUrl();

$("#url-open").addEventListener("click", () => {
  const u = $("#url-input").value.trim();
  if (u) window.open(u, "_blank"); else toast("Enter a URL first.");
});

$("#url-clear").addEventListener("click", () => { $("#url-input").value = ""; });

$("#url-save-btn").addEventListener("click", async () => {
  const url = $("#url-input").value.trim();
  await fetch("/api/url", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url })
  });
  toast("URL saved!");
});
