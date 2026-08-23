/* Vault — Admin SPA (vanilla JS, hash routing) */

const state = {
  token: localStorage.getItem("vault_token") || null,
  user: JSON.parse(localStorage.getItem("vault_user") || "null"),
  entries: [],
  users: [],
  audit: [],
  districts: [],
  blocks: [],
  selectedIds: new Set(),
  filters: { q: "", category: "", district_id: "", block_id: "", is_duplicate: "", tag: "", is_favorite: false, sort: "title" },
  searchTimer: null,
};

/* ---------------- API helpers ---------------- */

async function api(path, options = {}) {
  const headers = { ...(options.headers || {}) };
  if (state.token) headers["Authorization"] = `Bearer ${state.token}`;
  const resp = await fetch(path, { ...options, headers });
  if (resp.status === 401) {
    logout(false);
    throw new Error("Session expired — please log in again");
  }
  if (!resp.ok) {
    let detail = `Request failed (${resp.status})`;
    try {
      const body = await resp.json();
      if (body.detail) detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch (_) { /* ignore */ }
    throw new Error(detail);
  }
  if (resp.status === 204) return null;
  return resp.json();
}

function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 3000);
}

/* ---------------- Toast ---------------- */

function toast(message, type = "info") {
  const root = document.getElementById("toast-root");
  const el = document.createElement("div");
  el.className = `toast ${type}`;
  el.innerHTML = `<span class="dot"></span><span>${escapeHtml(message)}</span>`;
  root.appendChild(el);
  setTimeout(() => {
    el.classList.add("out");
    setTimeout(() => el.remove(), 260);
  }, 3200);
}

/* ---------------- Icons ---------------- */

const ICONS = {
  vault: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M12 3 5 5.5v5c0 4.6 3 8.6 7 9.5 4-.9 7-4.9 7-9.5v-5L12 3Z"/><path d="m9.5 11.5 1.8 1.8 3.4-3.6"/></svg>',
  search: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/></svg>',
  users: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="9" cy="8" r="3.5"/><path d="M2.5 20c.8-3.4 3.4-5 6.5-5s5.7 1.6 6.5 5"/><circle cx="17.5" cy="9" r="2.5"/><path d="M17 14.5c2.4.4 4 1.8 4.5 4"/></svg>',
  shield: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M12 3 5 5.5v5c0 4.6 3 8.6 7 9.5 4-.9 7-4.9 7-9.5v-5L12 3Z"/></svg>',
  clock: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg>',
  key: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="8" cy="15" r="4"/><path d="m11 12 9-9"/><path d="M17 6l3 3"/><path d="M14 9l2 2"/></svg>',
  edit: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M4 20h4L19.5 8.5a2.1 2.1 0 0 0-3-3L5 17l-1 4Z"/><path d="m14.5 6.5 3 3"/></svg>',
  trash: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M4 7h16"/><path d="M9 7V4h6v3"/><path d="M6 7l1 13h10l1-13"/><path d="M10 11v5M14 11v5"/></svg>',
  eye: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M2 12s3.5-6.5 10-6.5S22 12 22 12s-3.5 6.5-10 6.5S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/></svg>',
  copy: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="9" y="9" width="12" height="12" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>',
  up: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M12 19V5"/><path d="m5 12 7-7 7 7"/></svg>',
  down: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M12 5v14"/><path d="m19 12-7 7-7-7"/></svg>',
  plus: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 5v14M5 12h14"/></svg>',
  log: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M16 4h3a1 1 0 0 1 1 1v14a1 1 0 0 1-1 1h-3"/><path d="M8 20H5a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1h3"/><path d="M9 8h6M9 12h6M9 16h4"/></svg>',
  box: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="m12 3 8 4.5v9L12 21l-8-4.5v-9L12 3Z"/><path d="M4 7.5 12 12l8-4.5M12 12v9"/></svg>',
};

/* ---------------- Utils ---------------- */

function escapeHtml(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

function timeAgo(iso) {
  const then = new Date(iso).getTime();
  const diff = Date.now() - then;
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `${days}d ago`;
  return new Date(iso).toLocaleDateString();
}

function passwordStrength(pw) {
  let score = 0;
  if (pw.length >= 8) score++;
  if (pw.length >= 14) score++;
  if (/[A-Z]/.test(pw) && /[a-z]/.test(pw)) score++;
  if (/\d/.test(pw)) score++;
  if (/[^A-Za-z0-9]/.test(pw)) score++;
  if (score <= 1) return { label: "Weak", color: "#F87171", pct: 25 };
  if (score <= 3) return { label: "Fair", color: "#FBBF24", pct: 55 };
  if (score === 4) return { label: "Good", color: "#67E8F9", pct: 80 };
  return { label: "Strong", color: "#34D399", pct: 100 };
}

function hostOf(url) {
  try { return new URL(url.startsWith("http") ? url : `https://${url}`).hostname.replace(/^www\./, ""); } catch { return url || "—"; }
}

const CATEGORIES = ["email", "banking", "social", "shopping", "work", "entertainment", "other"];
const CATEGORY_PILL = { email: "cyan", banking: "amber", social: "violet", shopping: "green", work: "violet", entertainment: "cyan", other: "gray" };

function pillFor(cat) {
  const cls = CATEGORY_PILL[cat] || "gray";
  return `<span class="pill ${cls}">${escapeHtml(cat)}</span>`;
}

function debounce(fn, ms) {
  return (...args) => {
    clearTimeout(state.searchTimer);
    state.searchTimer = setTimeout(() => fn(...args), ms);
  };
}

/* ---------------- Modal helpers ---------------- */

function openModal(html, wide = false) {
  const root = document.getElementById("modal-root");
  root.innerHTML = `<div class="modal-backdrop" data-close="1"><div class="modal ${wide ? "modal-wide" : ""}">${html}</div></div>`;
  root.querySelector(".modal-backdrop").addEventListener("mousedown", (e) => {
    if (e.target.dataset.close) closeModal();
  });
  document.addEventListener("keydown", escHandler);
}

function escHandler(e) { if (e.key === "Escape") closeModal(); }

function closeModal() {
  document.removeEventListener("keydown", escHandler);
  document.getElementById("modal-root").innerHTML = "";
}

/* ---------------- Login view ---------------- */

function renderLogin() {
  document.getElementById("app").innerHTML = `
    <div class="login-shell">
      <div class="login-card">
        <div class="login-brand">
          <div class="brand-mark">◆</div>
          <div>
            <div class="login-title">Vault</div>
            <div class="login-sub">Admin console · password manager</div>
          </div>
        </div>
        <form id="login-form">
          <div class="form-error" id="login-error" style="display:none"></div>
          <div class="field">
            <label for="username">Username</label>
            <input class="input" id="username" name="username" autocomplete="username" required autofocus />
          </div>
          <div class="field">
            <label for="password">Password</label>
            <div class="pass-wrap">
              <input class="input" id="password" name="password" type="password" autocomplete="current-password" required />
              <button type="button" class="pass-toggle" data-toggle="password" title="Show password">${ICONS.eye}</button>
            </div>
          </div>
          <button type="submit" class="btn btn-primary btn-lg" id="login-btn" style="width:100%;justify-content:center">Unlock Vault</button>
        </form>
        <div class="login-hint">Admin-only console · Employees use the mobile app</div>
      </div>
    </div>`;

  document.getElementById("login-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const btn = document.getElementById("login-btn");
    const err = document.getElementById("login-error");
    btn.disabled = true;
    btn.textContent = "Unlocking…";
    err.style.display = "none";
    try {
      const { access_token } = await api("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username: document.getElementById("username").value, password: document.getElementById("password").value }),
      });
      state.token = access_token;
      state.user = await api("/api/auth/me");
      localStorage.setItem("vault_token", access_token);
      localStorage.setItem("vault_user", JSON.stringify(state.user));
      if (state.user.role !== "admin") {
        logout(false);
        err.textContent = "This console is for admins only.";
        err.style.display = "block";
        return;
      }
      location.hash = "#/vault";
    } catch (ex) {
      err.textContent = ex.message;
      err.style.display = "block";
    } finally {
      btn.disabled = false;
      btn.textContent = "Unlock Vault";
    }
  });

  document.querySelectorAll("[data-toggle]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const input = document.getElementById(btn.dataset.toggle);
      input.type = input.type === "password" ? "text" : "password";
    });
  });
}

/* ---------------- Layout ---------------- */

function shell(title, subtitle, content, activeNav) {
  return `
    <div class="app-shell">
      <aside class="sidebar">
        <div class="brand">
          <div class="brand-mark">◆</div>
          <div class="brand-name">Vault</div>
        </div>
        <button class="nav-item ${activeNav === "vault" ? "active" : ""}" data-nav="vault">${ICONS.vault}<span>Vault</span></button>
        <button class="nav-item ${activeNav === "users" ? "active" : ""}" data-nav="users">${ICONS.users}<span>Users</span></button>
        <button class="nav-item ${activeNav === "audit" ? "active" : ""}" data-nav="audit">${ICONS.log}<span>Audit log</span></button>
        <button class="nav-item ${activeNav === "districts" ? "active" : ""}" data-nav="districts">${ICONS.box}<span>Districts</span></button>
        <div class="sidebar-footer">
          <div class="user-chip">
            <div class="avatar">${escapeHtml((state.user?.username || "?").slice(0, 2))}</div>
            <div class="meta">
              <div class="name">${escapeHtml(state.user?.username)}</div>
              <div class="role">Admin</div>
            </div>
            <button class="icon-btn" id="logout-btn" title="Sign out">${ICONS.log}</button>
          </div>
        </div>
      </aside>
      <main class="main">
        <div class="view-enter">
          <h1 class="page-title">${title}</h1>
          <div class="page-sub">${subtitle}</div>
          ${content}
        </div>
      </main>
    </div>`;
}

function bindShell() {
  document.querySelectorAll("[data-nav]").forEach((btn) => {
    btn.addEventListener("click", () => { location.hash = `#/${btn.dataset.nav}`; });
  });
  const logoutBtn = document.getElementById("logout-btn");
  if (logoutBtn) logoutBtn.addEventListener("click", () => logout(true));
}

function logout(silent = true) {
  state.token = null;
  state.user = null;
  localStorage.removeItem("vault_token");
  localStorage.removeItem("vault_user");
  location.hash = "#/login";
  if (!silent) toast("Signed out");
}

/* ---------------- Vault view ---------------- */

async function loadEntries() {
  const params = new URLSearchParams();
  if (state.filters.q) params.set("q", state.filters.q);
  if (state.filters.category) params.set("category", state.filters.category);
  if (state.filters.district_id) params.set("district_id", state.filters.district_id);
  if (state.filters.block_id) params.set("block_id", state.filters.block_id);
  if (state.filters.is_duplicate) params.set("is_duplicate", state.filters.is_duplicate);
  if (state.filters.tag) params.set("tag", state.filters.tag);
  if (state.filters.is_favorite) params.set("is_favorite", "true");
  if (state.filters.sort && state.filters.sort !== "title") params.set("sort", state.filters.sort);
  try {
    state.entries = await api(`/api/entries?${params}`);
  } catch (e) {
    console.error("loadEntries failed", e);
    toast(e.message || "Failed to load entries", "error");
    state.entries = [];
  }
}

function renderVault() {
  const stats = vaultStats();
  document.getElementById("app").innerHTML = shell(
    "The Vault",
    "Every credential, encrypted at rest, one search away.",
    `
    <div class="bento">
      <div class="bento-card bento-lg">
        <div class="stat-rule"></div>
        <div class="stat-label">Saved credentials</div>
        <div class="stat-value grad-text">${stats.total}</div>
        <div class="stat-delta">${stats.categories} categories in use</div>
      </div>
      <div class="bento-card bento-sm">
        <div class="icon-bubble cyan">${ICONS.box}</div>
        <div class="stat-label">Recently updated</div>
        <div class="stat-value">${stats.recent}</div>
        <div class="stat-delta">in the last 7 days</div>
      </div>
      <div class="bento-card bento-sm">
        <div class="icon-bubble amber">${ICONS.shield}</div>
        <div class="stat-label">Top category</div>
        <div class="stat-value" style="font-size:1.5rem;padding-top:8px">${stats.topCategory}</div>
      </div>
      <div class="bento-card bento-sm">
        <div class="icon-bubble" style="background:#F87171">${ICONS.copy}</div>
        <div class="stat-label">Duplicates</div>
        <div class="stat-value">${stats.dup}</div>
        <div class="stat-delta">marked, not skipped</div>
      </div>
    </div>

    <div class="toolbar">
      <div class="search-box">${ICONS.search}<input id="search" placeholder="Search name/URL/tag… (smart)" value="${escapeHtml(state.filters.q)}" /></div>
      <input id="tag-search" placeholder="Tag" value="${escapeHtml(state.filters.tag)}" style="max-width:140px" class="input" />
      <button class="btn btn-primary" id="import-btn">${ICONS.up} Import</button>
      <button class="btn btn-ghost" id="export-csv-btn">${ICONS.down} CSV</button>
      <button class="btn btn-ghost" id="export-xlsx-btn">${ICONS.down} Excel</button>
      <button class="btn btn-ghost" id="add-btn">${ICONS.plus} New entry</button>
    </div>
    <div class="toolbar" style="margin-top:10px">
      <select id="filter-district" class="input" style="max-width:160px"><option value="">All districts</option>${state.districts.map(d=>`<option value="${d.id}" ${state.filters.district_id==d.id?"selected":""}>${escapeHtml(d.name)}</option>`).join("")}</select>
      <select id="filter-block" class="input" style="max-width:160px"><option value="">All blocks</option>${state.blocks.filter(b=>!state.filters.district_id || b.district_id==state.filters.district_id).map(b=>`<option value="${b.id}" ${state.filters.block_id==b.id?"selected":""}>${escapeHtml(b.name)}</option>`).join("")}</select>
      <label style="display:flex;align-items:center;gap:6px;font-size:13px"><input type="checkbox" id="filter-dup" ${state.filters.is_duplicate?"checked":""}/> Duplicates</label>
      <label style="display:flex;align-items:center;gap:6px;font-size:13px"><input type="checkbox" id="filter-fav" ${state.filters.is_favorite?"checked":""}/> Favorites</label>
      <select id="filter-sort" class="input" style="max-width:140px"><option value="title" ${state.filters.sort==="title"?"selected":""}>Sort: Title</option><option value="recent" ${state.filters.sort==="recent"?"selected":""}>Recent</option><option value="favorite" ${state.filters.sort==="favorite"?"selected":""}>Pinned first</option></select>
      <button class="btn btn-ghost" id="clear-filters">Clear</button>
    </div>
    <div id="bulk-bar" style="display:${state.selectedIds.size?"flex":"none"};gap:8px;align-items:center;margin:12px 0;padding:10px;background:var(--surface-2);border-radius:10px">
      <span>${state.selectedIds.size} selected</span>
      <select id="bulk-district" class="input" style="max-width:140px"><option value="">District</option>${state.districts.map(d=>`<option value="${d.id}">${escapeHtml(d.name)}</option>`).join("")}</select>
      <select id="bulk-block" class="input" style="max-width:140px"><option value="">Block</option>${state.blocks.map(b=>`<option value="${b.id}">${escapeHtml(b.name)}</option>`).join("")}</select>
      <button class="btn btn-primary" id="bulk-assign">Assign</button>
      <button class="btn btn-ghost" id="bulk-clear">Clear</button>
    </div>

    <div class="chip-row">
      <button class="chip ${!state.filters.category ? "active" : ""}" data-cat="">All</button>
      ${CATEGORIES.map((c) => `<button class="chip ${state.filters.category === c ? "active" : ""}" data-cat="${c}">${c}</button>`).join("")}
    </div>

    <div class="table-wrap">
      <table>
        <thead><tr><th><input type="checkbox" id="select-all" /></th><th>Name</th><th>URL</th><th>Scope</th><th>Tags</th><th>Category</th><th>Updated</th><th></th></tr></thead>
        <tbody id="entries-body"></tbody>
      </table>
      <div class="empty-state" id="entries-empty" style="display:none">
        <div class="big">🔍</div>
        <h3>No entries found</h3>
        <div>Try a different search, or import a CSV / Excel export from your browser.</div>
      </div>
    </div>`,
    "vault",
  );
  bindShell();
  bindVaultEvents();
}

function vaultStats() {
  const week = Date.now() - 7 * 86400000;
  const recent = state.entries.filter((e) => new Date(e.updated_at).getTime() > week).length;
  const counts = {};
  let dup = 0;
  state.entries.forEach((e) => { counts[e.category] = (counts[e.category] || 0) + 1; if(e.is_duplicate) dup++; });
  const top = Object.entries(counts).sort((a, b) => b[1] - a[1])[0];
  return {
    total: state.entries.length,
    categories: Object.keys(counts).length,
    recent,
    dup,
    topCategory: top ? `${top[0]} (${top[1]})` : "—",
  };
}

function renderEntryRows() {
  const body = document.getElementById("entries-body");
  const empty = document.getElementById("entries-empty");
  if (!state.entries.length) {
    body.innerHTML = "";
    empty.style.display = "block";
    return;
  }
  empty.style.display = "none";
  body.innerHTML = state.entries.map((e) => `
    <tr style="${e.is_duplicate?"background:rgba(248,113,113,0.06)":""}">
      <td><input type="checkbox" class="row-check" data-id="${e.id}" ${state.selectedIds.has(e.id)?"checked":""}/></td>
      <td class="strong">${escapeHtml(e.title)} ${e.is_duplicate?`<span class="pill red" style="margin-left:6px">dup</span>`:""} ${e.is_favorite?"★":""} ${e.is_pinned?"📌":""}</td>
      <td>${escapeHtml(hostOf(e.url))}</td>
      <td>${e.district_name?`<span class="pill violet">${escapeHtml(e.district_name)}</span>`:"<span class=\"pill gray\">—</span>"} ${e.block_name?`<span class="pill cyan">${escapeHtml(e.block_name)}</span>`:""}</td>
      <td>${(e.tags||[]).map(t=>`<span class="pill green" style="margin:2px">${escapeHtml(t)}</span>`).join("") || "—"}</td>
      <td>${pillFor(e.category)}</td>
      <td>${timeAgo(e.updated_at)}</td>
      <td>
        <div class="cell-actions">
          <button class="mini-btn" data-view="${e.id}" title="View">${ICONS.eye}</button>
          <button class="mini-btn" data-edit="${e.id}" title="Edit">${ICONS.edit}</button>
          <button class="mini-btn danger" data-del="${e.id}" title="Delete">${ICONS.trash}</button>
        </div>
      </td>
    </tr>`).join("");

  body.querySelectorAll("[data-view]").forEach((b) => b.addEventListener("click", () => viewEntry(Number(b.dataset.view))));
  body.querySelectorAll("[data-edit]").forEach((b) => b.addEventListener("click", () => openEntryForm(Number(b.dataset.edit))));
  body.querySelectorAll("[data-del]").forEach((b) => b.addEventListener("click", () => confirmDelete(Number(b.dataset.del))));
  body.querySelectorAll(".row-check").forEach((c)=> c.addEventListener("change", (e)=>{ const id=Number(e.target.dataset.id); if(e.target.checked) state.selectedIds.add(id); else state.selectedIds.delete(id); document.getElementById("bulk-bar").style.display=state.selectedIds.size?"flex":"none"; }));

}

function bindVaultEvents() {
  const search = document.getElementById("search");
  const tagSearch = document.getElementById("tag-search");
  const districtSel = document.getElementById("filter-district");
  const blockSel = document.getElementById("filter-block");
  const dupChk = document.getElementById("filter-dup");
  const favChk = document.getElementById("filter-fav");
  const sortSel = document.getElementById("filter-sort");
  const clearBtn = document.getElementById("clear-filters");
  search.addEventListener("input", debounce(async () => {
    state.filters.q = search.value.trim();
    await loadEntries();
    renderEntryRows();
  }, 280));
  if(tagSearch) tagSearch.addEventListener("input", debounce(async()=>{ state.filters.tag=tagSearch.value.trim(); await loadEntries(); renderEntryRows();},300));
  if(districtSel) districtSel.addEventListener("change", async()=>{ state.filters.district_id=districtSel.value; state.filters.block_id=""; await loadEntries(); renderVault(); });
  if(blockSel) blockSel.addEventListener("change", async()=>{ state.filters.block_id=blockSel.value; await loadEntries(); renderEntryRows(); });
  if(dupChk) dupChk.addEventListener("change", async()=>{ state.filters.is_duplicate=dupChk.checked?"true":""; await loadEntries(); renderEntryRows(); });
  if(favChk) favChk.addEventListener("change", async()=>{ state.filters.is_favorite=favChk.checked; await loadEntries(); renderEntryRows(); });
  if(sortSel) sortSel.addEventListener("change", async()=>{ state.filters.sort=sortSel.value; await loadEntries(); renderEntryRows(); });
  if(clearBtn) clearBtn.addEventListener("click", async()=>{ state.filters={q:"",category:"",district_id:"",block_id:"",is_duplicate:"",tag:"",is_favorite:false,sort:"title"}; await loadEntries(); renderVault(); });
  const bulkDistrict=document.getElementById("bulk-district"); const bulkBlock=document.getElementById("bulk-block"); const bulkAssign=document.getElementById("bulk-assign"); const bulkClear=document.getElementById("bulk-clear"); const selectAll=document.getElementById("select-all");
  if(bulkAssign) bulkAssign.addEventListener("click", async()=>{
    const ids=[...state.selectedIds]; if(!ids.length) return; const did=bulkDistrict.value?Number(bulkDistrict.value):null; const bid=bulkBlock.value?Number(bulkBlock.value):null; try{ await api(`/api/entries/bulk-assign?district_id=${did||""}&block_id=${bid||""}`, {method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify(ids)}); toast(`Assigned ${ids.length} entries`,"success"); state.selectedIds.clear(); await loadEntries(); renderEntryRows(); }catch(e){toast(e.message,"error");}
  });
  if(bulkClear) bulkClear.addEventListener("click", ()=>{ state.selectedIds.clear(); renderEntryRows(); document.getElementById("bulk-bar").style.display="none";});
  if(selectAll) selectAll.addEventListener("change", (e)=>{ if(e.target.checked){ state.entries.forEach(en=>state.selectedIds.add(en.id));} else state.selectedIds.clear(); renderEntryRows();});


  document.querySelectorAll("[data-cat]").forEach((chip) => {
    chip.addEventListener("click", async () => {
      state.filters.category = chip.dataset.cat;
      document.querySelectorAll("[data-cat]").forEach((c) => c.classList.toggle("active", c === chip));
      await loadEntries();
      renderEntryRows();
    });
  });

  document.getElementById("add-btn").addEventListener("click", () => openEntryForm());
  document.getElementById("import-btn").addEventListener("click", () => openImportWizard());
  document.getElementById("export-csv-btn").addEventListener("click", () => exportVault("csv"));
  document.getElementById("export-xlsx-btn").addEventListener("click", () => exportVault("xlsx"));
}

async function exportVault(format) {
  try {
    const resp = await fetch(`/api/export?format=${format}`, { headers: { Authorization: `Bearer ${state.token}` } });
    if (resp.status === 401) return logout(false);
    if (!resp.ok) throw new Error(`Export failed (${resp.status})`);
    downloadBlob(await resp.blob(), `vault-export.${format === "xlsx" ? "xlsx" : "csv"}`);
    toast(`Exported ${state.entries.length} entries`, "success");
  } catch (ex) { toast(ex.message, "error"); }
}

/* ---------------- Entry modal ---------------- */

async function viewEntry(id) {
  try {
    const e = await api(`/api/entries/${id}`);
    const strength = passwordStrength(e.password);
    openModal(`
      <div class="modal-head">
        <div class="modal-title">${escapeHtml(e.title)}</div>
        <button class="modal-close" data-close="1">×</button>
      </div>
      <div class="field"><label>URL</label><div class="input" style="background:none;border:none;padding-left:0">${escapeHtml(e.url || "—")}</div></div>
      <div class="form-row">
        <div class="field"><label>Username</label><div style="display:flex;gap:8px;align-items:center">
          <div style="flex:1;word-break:break-all">${escapeHtml(e.username || "—")}</div>
          <button class="mini-btn" id="copy-username" title="Copy">${ICONS.copy}</button>
        </div></div>
        <div class="field">
          <label>Password</label>
          <div style="display:flex;gap:8px;align-items:center">
            <div style="flex:1;word-break:break-all" id="view-pw">••••••••••</div>
            <button class="mini-btn" id="reveal-pw" title="Reveal">${ICONS.eye}</button>
            <button class="mini-btn" id="copy-pw" title="Copy">${ICONS.copy}</button>
          </div>
          <div class="strength-bar"><div class="strength-fill" style="width:${strength.pct}%;background:${strength.color}"></div></div>
        </div>
      </div>
      <div class="field"><label>Notes</label><div style="color:var(--text-2);white-space:pre-wrap">${escapeHtml(e.notes || "—")}</div></div>
      <div class="field" style="display:flex;gap:6px;flex-wrap:wrap">${e.district_name?`<span class="pill violet">${escapeHtml(e.district_name)}</span>`:""} ${e.block_name?`<span class="pill cyan">${escapeHtml(e.block_name)}</span>`:""} ${e.is_duplicate?`<span class="pill red">duplicate</span>`:""} ${pillFor(e.category)} ${(e.tags||[]).map(t=>`<span class="pill green">${escapeHtml(t)}</span>`).join("")}</div>
      <div class="field" style="display:flex;gap:8px"><input id="new-tag" placeholder="Add private tag" class="input" style="flex:1"/><button class="btn btn-ghost" id="add-tag-btn">Add tag</button><button class="btn btn-ghost" id="fav-btn">${e.is_favorite?"★ Unfavorite":"☆ Favorite"}</button></div>
      <div class="modal-foot">
        <button class="btn btn-ghost" data-close="1">Close</button>
        <button class="btn btn-primary" id="edit-from-view">Edit</button>
      </div>
    `);
    let revealed = false;
    document.getElementById("reveal-pw").addEventListener("click", () => {
      revealed = !revealed;
      document.getElementById("view-pw").textContent = revealed ? e.password : "••••••••••";
    });
    document.getElementById("copy-pw").addEventListener("click", () => copyText(e.password, "Password copied"));
    document.getElementById("copy-username").addEventListener("click", () => copyText(e.username, "Username copied"));
    const tagBtn=document.getElementById("add-tag-btn"); if(tagBtn) tagBtn.addEventListener("click", async()=>{ const v=document.getElementById("new-tag").value.trim(); if(!v) return; try{ await api(`/api/entries/${e.id}/tags`,{method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify({tag:v})}); toast("Tag added","success"); closeModal(); viewEntry(e.id); }catch(ex){toast(ex.message,"error");}});
    const favBtn=document.getElementById("fav-btn"); if(favBtn) favBtn.addEventListener("click", async()=>{ try{ await api(`/api/entries/${e.id}/meta`,{method:"PUT", headers:{"Content-Type":"application/json"}, body: JSON.stringify({is_favorite: !e.is_favorite})}); toast(e.is_favorite?"Unfavorited":"Favorited","success"); closeModal(); viewEntry(e.id);}catch(ex){toast(ex.message,"error");}});
    document.getElementById("edit-from-view").addEventListener("click", () => { closeModal(); openEntryForm(e.id); });
  } catch (ex) { toast(ex.message, "error"); }
}

async function copyText(text, msg) {
  try { await navigator.clipboard.writeText(text); toast(msg, "success"); }
  catch { toast("Clipboard unavailable", "error"); }
}

function openEntryForm(entryId = null) {
  const existing = entryId ? state.entries.find((e) => e.id === entryId) : null;
  openModal(`
    <div class="modal-head">
      <div class="modal-title">${existing ? "Edit entry" : "New entry"}</div>
      <button class="modal-close" data-close="1">×</button>
    </div>
    <form id="entry-form">
      <div class="form-error" id="entry-error" style="display:none"></div>
      <div class="field"><label>Title</label><input class="input" id="f-title" required maxlength="255" value="${escapeHtml(existing?.title || "")}" placeholder="e.g. Gmail" /></div>
      <div class="field"><label>URL</label><input class="input" id="f-url" maxlength="1024" value="${escapeHtml(existing?.url || "")}" placeholder="https://mail.google.com" /></div>
      <div class="form-row">
        <div class="field"><label>Username</label><input class="input" id="f-username" value="${escapeHtml(existing?.username || "")}" /></div>
        <div class="field"><label>Category</label>
          <select class="input" id="f-category">${CATEGORIES.map((c) => `<option value="${c}" ${existing?.category === c ? "selected" : ""}>${c}</option>`).join("")}</select>
        </div>
      </div>
      <div class="form-row">
        <div class="field"><label>District</label><select class="input" id="f-district"><option value="">— Unassigned</option>${state.districts.map(d=>`<option value="${d.id}" ${existing?.district_id===d.id?"selected":""}>${escapeHtml(d.name)}</option>`).join("")}</select></div>
        <div class="field"><label>Block</label><select class="input" id="f-block"><option value="">— Unassigned</option>${state.blocks.map(b=>`<option value="${b.id}" ${existing?.block_id===b.id?"selected":""}>${escapeHtml(b.name)}</option>`).join("")}</select></div>
      </div>
      <div class="field">
        <label>Password</label>
        <div class="pass-wrap">
          <input class="input" id="f-password" type="password" required value="${escapeHtml(existing?.password || "")}" placeholder="••••••••" />
          <button type="button" class="pass-toggle" data-toggle="f-password" title="Show">${ICONS.eye}</button>
        </div>
        <div class="strength-bar"><div class="strength-fill" id="f-strength" style="width:0"></div></div>
      </div>
      <div class="field"><label>Notes</label><textarea class="input" id="f-notes" rows="3" maxlength="4096" placeholder="Optional">${escapeHtml(existing?.notes || "")}</textarea></div>
      <div class="modal-foot">
        <button type="button" class="btn btn-ghost" data-close="1">Cancel</button>
        <button type="submit" class="btn btn-primary">${existing ? "Save changes" : "Add entry"}</button>
      </div>
    </form>`);

  const pw = document.getElementById("f-password");
  const strength = document.getElementById("f-strength");
  const updateStrength = () => {
    const s = passwordStrength(pw.value);
    strength.style.width = `${s.pct}%`;
    strength.style.background = s.color;
  };
  pw.addEventListener("input", updateStrength);
  updateStrength();

  document.getElementById("entry-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const err = document.getElementById("entry-error");
    const payload = {
      title: document.getElementById("f-title").value.trim(),
      url: document.getElementById("f-url").value.trim(),
      username: document.getElementById("f-username").value.trim(),
      password: document.getElementById("f-password").value,
      notes: document.getElementById("f-notes").value.trim(),
      category: document.getElementById("f-category").value,
      district_id: document.getElementById("f-district").value?Number(document.getElementById("f-district").value):null,
      block_id: document.getElementById("f-block").value?Number(document.getElementById("f-block").value):null,
    };
    if (!payload.title || !payload.password) {
      err.textContent = "Title and password are required";
      err.style.display = "block";
      return;
    }
    try {
      const path = existing ? `/api/entries/${existing.id}` : "/api/entries";
      const method = existing ? "PUT" : "POST";
      await api(path, { method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
      toast(existing ? "Entry updated" : "Entry added", "success");
      closeModal();
      await loadEntries();
      renderEntryRows();
    } catch (ex) {
      err.textContent = ex.message;
      err.style.display = "block";
    }
  });
}

function confirmDelete(id) {
  const entry = state.entries.find((e) => e.id === id);
  openModal(`
    <div class="modal-head"><div class="modal-title">Delete entry?</div></div>
    <p style="color:var(--text-2);font-size:14.5px">This permanently removes <strong style="color:var(--text-1)">${escapeHtml(entry?.title || "")}</strong> and its credentials. This cannot be undone.</p>
    <div class="modal-foot">
      <button class="btn btn-ghost" data-close="1">Cancel</button>
      <button class="btn btn-danger" id="confirm-del">${ICONS.trash} Delete</button>
    </div>`);
  document.getElementById("confirm-del").addEventListener("click", async () => {
    try {
      await api(`/api/entries/${id}`, { method: "DELETE" });
      toast("Entry deleted", "success");
      closeModal();
      await loadEntries();
      renderEntryRows();
    } catch (ex) { toast(ex.message, "error"); }
  });
}

/* ---------------- Import wizard ---------------- */

const BROWSER_GUIDES = {
  chrome: [
    ["Open <strong>Chrome</strong> on your computer."],
    ["Click your profile picture, then <strong>Passwords</strong> (or go to <code>chrome://password-manager/passwords</code>)."],
    ["Click the three-dot menu → <strong>Export passwords</strong>."],
    ["Confirm your computer password when prompted."],
    ["Save the resulting <code>.csv</code> file and upload it here."],
  ],
  edge: [
    ["Open <strong>Edge</strong>, go to <code>edge://settings/passwords</code>."],
    ["Click the three-dot menu next to “Saved passwords” → <strong>Export passwords</strong>."],
    ["Confirm with your Windows password."],
    ["Save the <code>.csv</code> file and upload it here."],
  ],
  firefox: [
    ["Open <strong>Firefox</strong>, go to <code>about:logins</code>."],
    ["Click the three-dot menu (…) → <strong>Export logins…</strong>."],
    ["Confirm to export, save the <code>.csv</code> file and upload it here."],
  ],
  safari: [
    ["On <strong>macOS</strong>: open Safari → Settings → Passwords, unlock, and export via third-party tools (Safari has no native CSV export)."],
    ["Alternative: use iCloud Keychain export through <strong>iCloud Passwords for Windows</strong> → export as CSV."],
    ["Upload the <code>.csv</code> file here."],
  ],
  bitwarden: [
    ["Open <strong>Bitwarden</strong> vault (web vault recommended)."],
    ["Tools → <strong>Export vault</strong> → format <strong>.csv</strong>."],
    ["Confirm by entering your master password."],
    ["Save and upload the file here."],
  ],
  onepassword: [
    ["Open <strong>1Password</strong> → click your account → <strong>Export</strong>."],
    ["Choose format <strong>.csv</strong> and include fields Title, Url, Username, Password."],
    ["Save and upload the file here."],
  ],
};

function openImportWizard() {
  openModal(`
    <div class="modal-head">
      <div class="modal-title">Import passwords</div>
      <button class="modal-close" data-close="1">×</button>
    </div>
    <div class="steps">
      <div class="step active" id="step-1">1 · Source</div>
      <div class="step" id="step-2">2 · File</div>
      <div class="step" id="step-3">3 · Preview</div>
    </div>
    <div id="wizard-body"></div>
  `, true);

  renderWizardStep1();
  let previewData = null;

  function setStep(n) {
    for (let i = 1; i <= 3; i++) document.getElementById(`step-${i}`).classList.toggle("active", i === n);
  }

  function renderWizardStep1() {
    setStep(1);
    const body = document.getElementById("wizard-body");
    body.innerHTML = `
      <div class="guide-box">
        <div style="font-weight:600;color:var(--text-1);margin-bottom:4px">Where did your passwords come from?</div>
        <div style="font-size:13px;color:var(--text-3)">We'll show you the exact export steps for that source.</div>
      </div>
      <div class="chip-row" id="browser-chips">
        ${Object.keys(BROWSER_GUIDES).map((b) => `<button class="chip" data-browser="${b}">${b}</button>`).join("")}
      </div>
      <div class="guide-box" id="guide-box" style="display:none">
        <strong>Export steps</strong>
        <ol></ol>
      </div>
      <div class="modal-foot">
        <button class="btn btn-ghost" data-close="1">Cancel</button>
        <button class="btn btn-primary" id="wiz-next" disabled>Next — choose file</button>
      </div>`;

    let selected = null;
    body.querySelectorAll("[data-browser]").forEach((chip) => {
      chip.addEventListener("click", () => {
        selected = chip.dataset.browser;
        body.querySelectorAll("[data-browser]").forEach((c) => c.classList.toggle("active", c === chip));
        const box = document.getElementById("guide-box");
        box.style.display = "block";
        box.querySelector("ol").innerHTML = BROWSER_GUIDES[selected].map(([li]) => `<li>${li}</li>`).join("");
        document.getElementById("wiz-next").disabled = false;
      });
    });
    document.getElementById("wiz-next").addEventListener("click", () => renderWizardStep2());
  }

  function renderWizardStep2() {
    setStep(2);
    const body = document.getElementById("wizard-body");
    body.innerHTML = `
      <div class="guide-box" style="font-size:13.5px;color:var(--text-3)">Supports <strong style="color:var(--text-1)">.csv</strong> from Chrome, Edge, Firefox, Bitwarden, 1Password — and <strong style="color:var(--text-1)">.xlsx</strong> spreadsheets. Duplicates are <b>imported and marked</b> (not skipped) — delete via filter if needed.</div>
      <div style="display:flex;gap:10px;margin:12px 0"><select id="wiz-district" class="input" style="flex:1"><option value="">— Assign district (optional)</option>${state.districts.map(d=>`<option value="${d.id}">${escapeHtml(d.name)}</option>`).join("")}</select><select id="wiz-block" class="input" style="flex:1"><option value="">— Assign block (optional)</option>${state.blocks.map(b=>`<option value="${b.id}">${escapeHtml(b.name)}</option>`).join("")}</select></div>
      <div style="display:flex;gap:10px;margin-bottom:12px"><label style="font-size:13px;display:flex;align-items:center;gap:6px">Dedup mode <select id="wiz-dedup" class="input" style="width:140px"><option value="none">Import all</option><option value="title_url">Title+URL</option><option value="exact">Exact</option></select></label><label style="font-size:13px;display:flex;align-items:center;gap:6px"><input type="checkbox" id="wiz-skip" /> Skip (old)</label></div>
      <div class="dropzone" id="dropzone">
        <div class="dz-icon">📂</div>
        <div>Drag & drop your file here, or <strong>click to browse</strong></div>
        <div style="font-size:12px;margin-top:6px">Max 50,000 rows</div>
      </div>
      <input type="file" id="file-input" accept=".csv,.xlsx,.xlsm" style="display:none" />
      <div class="modal-foot">
        <button class="btn btn-ghost" id="wiz-back-1">Back</button>
      </div>`;

    const dz = document.getElementById("dropzone");
    const input = document.getElementById("file-input");
    dz.addEventListener("click", () => input.click());
    dz.addEventListener("dragover", (e) => { e.preventDefault(); dz.classList.add("drag"); });
    dz.addEventListener("dragleave", () => dz.classList.remove("drag"));
    dz.addEventListener("drop", (e) => { e.preventDefault(); dz.classList.remove("drag"); if (e.dataTransfer.files[0]) handleFile(e.dataTransfer.files[0]); });
    input.addEventListener("change", () => { if (input.files[0]) handleFile(input.files[0]); });
    document.getElementById("wiz-back-1").addEventListener("click", renderWizardStep1);

    async function handleFile(file) {
      const form = new FormData();
      form.append("file", file);
      try {
        const res = await api("/api/import/preview", { method: "POST", body: form });
        previewData = { file, ...res };
        renderWizardStep3();
      } catch (ex) { toast(ex.message, "error"); }
    }
  }

  function renderWizardStep3() {
    setStep(3);
    const body = document.getElementById("wizard-body");
    const p = previewData;
    body.innerHTML = `
      <div class="preview-panel">
        <div class="preview-meta">
          <span class="pill violet">${escapeHtml(p.detected_format)}</span>
          <span class="pill green">${p.total_rows} rows parsed</span>
          <span class="pill gray">${escapeHtml(p.file.name)}</span>
        </div>
        <div class="table-wrap" style="border-radius:12px">
          <table>
            <thead><tr><th>Title</th><th>URL</th><th>Username</th><th>Password</th><th>Category</th></tr></thead>
            <tbody>
              ${p.sample.map((r) => `<tr><td class="strong">${escapeHtml(r.title)}</td><td>${escapeHtml(hostOf(r.url))}</td><td>${escapeHtml(r.username || "—")}</td><td>${escapeHtml(r.password.replace(/./g, "•"))}</td><td>${pillFor(r.category)}</td></tr>`).join("")}
            </tbody>
          </table>
        </div>
        <div class="sample-note">Showing first ${p.sample.length} of ${p.total_rows} rows. Duplicates are skipped automatically.</div>
      </div>
      <div class="modal-foot">
        <button class="btn btn-ghost" id="wiz-back-2">Back</button>
        <button class="btn btn-primary" id="wiz-confirm">${ICONS.box} Import ${p.total_rows} passwords</button>
      </div>`;

    document.getElementById("wiz-back-2").addEventListener("click", renderWizardStep2);
    document.getElementById("wiz-confirm").addEventListener("click", async (e) => {
      const btn = e.currentTarget;
      btn.disabled = true;
      btn.textContent = "Importing…";
      const form = new FormData();
      form.append("file", p.file);
      form.append("mapping", JSON.stringify(p.mapping));
      const did=document.getElementById("wiz-district")?.value; const bid=document.getElementById("wiz-block")?.value; const dedup=document.getElementById("wiz-dedup")?.value||"none"; const skip=document.getElementById("wiz-skip")?.checked; if(did) form.append("district_id", did); if(bid) form.append("block_id", bid); form.append("dedup_mode", dedup); form.append("skip_duplicates", skip?"true":"false");
      try {
        const res = await api("/api/import/confirm", { method: "POST", body: form });
        closeModal();
        toast(`Imported ${res.imported}, skipped ${res.skipped_duplicates} duplicate${res.skipped_duplicates === 1 ? "" : "s"}${res.failed ? `, ${res.failed} failed` : ""}`, res.failed ? "info" : "success");
        await loadEntries();
        renderVault();
      } catch (ex) {
        toast(ex.message, "error");
        btn.disabled = false;
        btn.textContent = `Import ${p.total_rows} passwords`;
      }
    });
  }
}

/* ---------------- Users view ---------------- */

async function loadUsers() {
  state.users = await api("/api/users");
}

async function loadDistricts() {
  try { state.districts = await api("/api/districts"); } catch(e){ state.districts=[]; }
}
async function loadBlocks() {
  try { state.blocks = await api("/api/blocks"); } catch(e){ state.blocks=[]; }
}

async function renderUsers() {
  await Promise.all([loadDistricts(), loadBlocks()]);
  document.getElementById("app").innerHTML = shell(
    "Users",
    "Admins manage the vault; employees can only view credentials from the mobile app.",
    `
    <div class="toolbar">
      <button class="btn btn-primary" id="add-user-btn">${ICONS.plus} Add user</button>
    </div>
    <div style="font-size:13px;color:var(--text-3);margin:8px 0">District employee → sees District+Blocks; Block employee → sees only its Block. Assign via add/edit.</div>
    <div class="table-wrap">
      <table>
        <thead><tr><th>Username</th><th>Role</th><th>Status</th><th>Created</th><th></th></tr></thead>
        <tbody id="users-body"></tbody>
      </table>
    </div>`,
    "users",
  );
  bindShell();
  renderUserRows();
  document.getElementById("add-user-btn").addEventListener("click", openUserForm);
}

function renderUserRows() {
  const body = document.getElementById("users-body");
  body.innerHTML = state.users.map((u) => `
    <tr>
      <td class="strong">${escapeHtml(u.username)}</td>
      <td><span class="role-badge" style="color:${u.role === "admin" ? "#A78BFA" : "#67E8F9"}">${u.role}</span> ${u.district_name?`<span class="pill violet">${escapeHtml(u.district_name)}</span>`:""} ${u.block_name?`<span class="pill cyan">${escapeHtml(u.block_name)}</span>`:""}</td>
      <td>${u.is_active ? '<span class="pill green">Active</span>' : '<span class="pill red">Disabled</span>'}</td>
      <td>${new Date(u.created_at).toLocaleDateString()}</td>
      <td>
        <div class="cell-actions">
          <button class="mini-btn" data-reset="${u.id}" title="Reset password">${ICONS.key}</button>
          ${u.role !== "admin" || state.user.username !== u.username ? `
          <button class="mini-btn ${u.role === "admin" ? "" : ""}" data-toggle-user="${u.id}" title="${u.is_active ? "Disable" : "Enable"}">${ICONS.shield}</button>
          <button class="mini-btn danger" data-del-user="${u.id}" title="Delete">${ICONS.trash}</button>` : ""}
        </div>
      </td>
    </tr>`).join("");

  body.querySelectorAll("[data-reset]").forEach((b) => b.addEventListener("click", () => resetPassword(Number(b.dataset.reset))));
  body.querySelectorAll("[data-toggle-user]").forEach((b) => b.addEventListener("click", () => toggleUser(Number(b.dataset.toggleUser))));
  body.querySelectorAll("[data-del-user]").forEach((b) => b.addEventListener("click", () => deleteUser(Number(b.dataset.delUser))));
}

function openUserForm() {
  openModal(`
    <div class="modal-head"><div class="modal-title">Add user</div><button class="modal-close" data-close="1">×</button></div>
    <form id="user-form">
      <div class="form-error" id="user-error" style="display:none"></div>
      <div class="field"><label>Username</label><input class="input" id="u-name" required minlength="3" pattern="[a-zA-Z0-9_.-]+" placeholder="employee.name" /></div>
      <div class="field"><label>Password</label><input class="input" id="u-pass" type="password" required minlength="8" /></div>
      <div class="field"><label>Role</label>
        <select class="input" id="u-role">
          <option value="employee" selected>Employee — read-only mobile access</option>
          <option value="admin">Admin — full web console access</option>
        </select>
      </div>
      <div class="form-row"><div class="field"><label>District</label><select class="input" id="u-district"><option value="">— None (legacy, sees all)</option>${state.districts.map(d=>`<option value="${d.id}">${escapeHtml(d.name)}</option>`).join("")}</select></div><div class="field"><label>Block</label><select class="input" id="u-block"><option value="">— None (district-level if district set)</option>${state.blocks.map(b=>`<option value="${b.id}">${escapeHtml(b.name)} — ${escapeHtml(state.districts.find(d=>d.id===b.district_id)?.name||"")}</option>`).join("")}</select></div></div>
      <div style="font-size:12px;color:var(--text-3)">Block employee sees only its Block; District employee sees District+Blocks.</div>
      <div class="modal-foot">
        <button type="button" class="btn btn-ghost" data-close="1">Cancel</button>
        <button type="submit" class="btn btn-primary">Create user</button>
      </div>
    </form>`);
  document.getElementById("user-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const err = document.getElementById("user-error");
    try {
      await api("/api/users", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          username: document.getElementById("u-name").value.trim(),
          password: document.getElementById("u-pass").value,
          role: document.getElementById("u-role").value,
          district_id: document.getElementById("u-district").value?Number(document.getElementById("u-district").value):null,
          block_id: document.getElementById("u-block").value?Number(document.getElementById("u-block").value):null,
        }),
      });
      toast("User created", "success");
      closeModal();
      await loadUsers();
      renderUserRows();
    } catch (ex) {
      err.textContent = ex.message;
      err.style.display = "block";
    }
  });
}

function resetPassword(id) {
  const user = state.users.find((u) => u.id === id);
  openModal(`
    <div class="modal-head"><div class="modal-title">Reset password</div><button class="modal-close" data-close="1">×</button></div>
    <p style="color:var(--text-2);font-size:14.5px;margin-bottom:16px">New password for <strong style="color:var(--text-1)">${escapeHtml(user?.username)}</strong> (min 8 characters).</p>
    <div class="field"><label>New password</label><input class="input" id="r-pass" type="password" required minlength="8" /></div>
    <div class="modal-foot">
      <button class="btn btn-ghost" data-close="1">Cancel</button>
      <button class="btn btn-primary" id="r-confirm">Set password</button>
    </div>`);
  document.getElementById("r-confirm").addEventListener("click", async () => {
    const pw = document.getElementById("r-pass").value;
    if (pw.length < 8) return toast("Minimum 8 characters", "error");
    try {
      await api(`/api/users/${id}`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ password: pw }) });
      toast("Password updated", "success");
      closeModal();
    } catch (ex) { toast(ex.message, "error"); }
  });
}

function toggleUser(id) {
  const user = state.users.find((u) => u.id === id);
  if (!user) return;
  openModal(`
    <div class="modal-head"><div class="modal-title">${user.is_active ? "Disable" : "Enable"} user</div><button class="modal-close" data-close="1">×</button></div>
    <p style="color:var(--text-2);font-size:14.5px"><strong style="color:var(--text-1)">${escapeHtml(user.username)}</strong> will be ${user.is_active ? "blocked from signing in" : "allowed to sign in again"}.</p>
    <div class="modal-foot">
      <button class="btn btn-ghost" data-close="1">Cancel</button>
      <button class="btn ${user.is_active ? "btn-danger" : "btn-primary"}" id="t-confirm">${user.is_active ? "Disable" : "Enable"}</button>
    </div>`);
  document.getElementById("t-confirm").addEventListener("click", async () => {
    try {
      await api(`/api/users/${id}`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ is_active: !user.is_active }) });
      toast(`User ${user.is_active ? "disabled" : "enabled"}`, "success");
      closeModal();
      await loadUsers();
      renderUserRows();
    } catch (ex) { toast(ex.message, "error"); }
  });
}

function deleteUser(id) {
  const user = state.users.find((u) => u.id === id);
  openModal(`
    <div class="modal-head"><div class="modal-title">Delete user?</div><button class="modal-close" data-close="1">×</button></div>
    <p style="color:var(--text-2);font-size:14.5px"><strong style="color:var(--text-1)">${escapeHtml(user?.username)}</strong> loses access immediately. This cannot be undone.</p>
    <div class="modal-foot">
      <button class="btn btn-ghost" data-close="1">Cancel</button>
      <button class="btn btn-danger" id="d-confirm">${ICONS.trash} Delete</button>
    </div>`);
  document.getElementById("d-confirm").addEventListener("click", async () => {
    try {
      await api(`/api/users/${id}`, { method: "DELETE" });
      toast("User deleted", "success");
      closeModal();
      await loadUsers();
      renderUserRows();
    } catch (ex) { toast(ex.message, "error"); }
  });
}

/* ---------------- Audit view ---------------- */

async function loadAudit() {
  state.audit = await api("/api/audit");
}

const ACTION_COLOR = {
  "login.success": "green", "login.failed": "red",
  "entry.create": "cyan", "entry.update": "cyan", "entry.delete": "red",
  "user.create": "violet", "user.update": "violet", "user.delete": "red",
  "import.run": "green", "export.run": "amber",
};

function renderAudit() {
  document.getElementById("app").innerHTML = shell(
    "Audit log",
    "Every sensitive action, timestamped — who, what, when.",
    `
    <div class="table-wrap">
      <table>
        <thead><tr><th>Time</th><th>User</th><th>Action</th><th>Target</th><th>Detail</th></tr></thead>
        <tbody id="audit-body"></tbody>
      </table>
    </div>`,
    "audit",
  );
  bindShell();
  const body = document.getElementById("audit-body");
  body.innerHTML = state.audit.map((a) => `
    <tr>
      <td>${new Date(a.timestamp).toLocaleString()}</td>
      <td class="strong">${escapeHtml(a.user_id ? (state.users.find((u) => u.id === a.user_id)?.username ?? `#${a.user_id}`) : "—")}</td>
      <td><span class="pill ${ACTION_COLOR[a.action] || "gray"}">${escapeHtml(a.action)}</span></td>
      <td>${escapeHtml(a.target)}</td>
      <td>${escapeHtml(a.detail)}</td>
    </tr>`).join("") || '<tr><td colspan="5" class="empty-state">No activity yet</td></tr>';
}

/* ---------------- Districts view ---------------- */
function renderDistricts() {
  document.getElementById("app").innerHTML = shell(
    "Districts & Blocks",
    "Admin creates districts and blocks — then assigns entries and users to a scope.",
    `<div class="toolbar"><button class="btn btn-primary" id="add-district">+ District</button> <button class="btn btn-ghost" id="add-block">+ Block</button></div>
     <div class="table-wrap"><h3 style="margin:12px">Districts</h3><table><thead><tr><th>Name</th><th>Blocks</th><th></th></tr></thead><tbody id="district-body"></tbody></table></div>
     <div class="table-wrap" style="margin-top:16px"><h3 style="margin:12px">Blocks</h3><table><thead><tr><th>Name</th><th>District</th><th></th></tr></thead><tbody id="block-body"></tbody></table></div>`,
    "districts"
  );
  bindShell();
  const dBody=document.getElementById("district-body"); dBody.innerHTML=state.districts.map(d=>`<tr><td>${escapeHtml(d.name)}</td><td>${state.blocks.filter(b=>b.district_id===d.id).length}</td><td><button class="mini-btn danger" data-del-district="${d.id}">${ICONS.trash}</button></td></tr>`).join("")||"<tr><td colspan=3>—</td></tr>";
  const bBody=document.getElementById("block-body"); bBody.innerHTML=state.blocks.map(b=>`<tr><td>${escapeHtml(b.name)}</td><td>${escapeHtml(state.districts.find(d=>d.id===b.district_id)?.name||"")}</td><td><button class="mini-btn danger" data-del-block="${b.id}">${ICONS.trash}</button></td></tr>`).join("")||"<tr><td colspan=3>—</td></tr>";
  dBody.querySelectorAll("[data-del-district]").forEach(b=> b.addEventListener("click", async()=>{ try{ await api(`/api/districts/${b.dataset.delDistrict}`,{method:"DELETE"}); toast("District deleted","success"); await loadDistricts(); await loadBlocks(); renderDistricts();}catch(e){toast(e.message,"error");}}));
  bBody.querySelectorAll("[data-del-block]").forEach(b=> b.addEventListener("click", async()=>{ try{ await api(`/api/blocks/${b.dataset.delBlock}`,{method:"DELETE"}); toast("Block deleted","success"); await loadBlocks(); renderDistricts();}catch(e){toast(e.message,"error");}}));
  document.getElementById("add-district").addEventListener("click", ()=>{ openModal(`<div class="modal-head"><div class="modal-title">Add district</div><button class="modal-close" data-close="1">×</button></div><div class="field"><label>Name</label><input class="input" id="d-name" /></div><div class="modal-foot"><button class="btn btn-ghost" data-close="1">Cancel</button><button class="btn btn-primary" id="d-create">Create</button></div>`); document.getElementById("d-create").addEventListener("click", async()=>{ const n=document.getElementById("d-name").value.trim(); if(!n) return; try{ await api("/api/districts",{method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify({name:n})}); toast("District created","success"); closeModal(); await loadDistricts(); renderDistricts(); }catch(e){toast(e.message,"error");}});});
  document.getElementById("add-block").addEventListener("click", ()=>{ openModal(`<div class="modal-head"><div class="modal-title">Add block</div><button class="modal-close" data-close="1">×</button></div><div class="field"><label>District</label><select class="input" id="b-district">${state.districts.map(d=>`<option value="${d.id}">${escapeHtml(d.name)}</option>`).join("")}</select></div><div class="field"><label>Block name</label><input class="input" id="b-name" /></div><div class="modal-foot"><button class="btn btn-ghost" data-close="1">Cancel</button><button class="btn btn-primary" id="b-create">Create</button></div>`); document.getElementById("b-create").addEventListener("click", async()=>{ const n=document.getElementById("b-name").value.trim(); const did=Number(document.getElementById("b-district").value); if(!n) return; try{ await api("/api/blocks",{method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify({name:n, district_id:did})}); toast("Block created","success"); closeModal(); await loadBlocks(); renderDistricts(); }catch(e){toast(e.message,"error");}});});
}

/* ---------------- Router ---------------- */

async function router() {
  const route = location.hash.replace(/^#/, "") || "/vault";
  if (!state.token) return renderLogin();

  try {
    await Promise.allSettled([api("/api/auth/me")]);
  } catch (ex) {
    return renderLogin();
  }

  if (route.startsWith("/login")) return renderLogin();

  if (!state.user || state.user.role !== "admin") return renderLogin();

  if (route.startsWith("/vault")) {
    await Promise.allSettled([loadDistricts(), loadBlocks()]);
    await loadEntries();
    try {
      renderVault();
      renderEntryRows();
    } catch (e) {
      console.error("renderVault failed", e);
      document.getElementById("app").innerHTML = `<div style="padding:32px"><h3>Vault failed to load</h3><p>${escapeHtml(e.message)}</p><p><a href="#/login" class="btn btn-primary">Back to login</a></p></div>`;
    }
  } else if (route.startsWith("/users")) {
    await Promise.all([loadUsers(), loadAudit()]);
    renderUsers();
  } else if (route.startsWith("/audit")) {
    await Promise.all([loadUsers(), loadAudit()]);
    renderAudit();
  } else if (route.startsWith("/districts")) {
    await Promise.all([loadDistricts(), loadBlocks()]);
    renderDistricts();
  }
}

window.addEventListener("hashchange", router);
router();
