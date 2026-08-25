/* Vault — Admin SPA (vanilla JS, hash routing) */

const state = {
  token: localStorage.getItem("vault_token") || null,
  user: JSON.parse(localStorage.getItem("vault_user") || "null"),
  entries: [],
  users: [],
  audit: [],
  districts: [],
  blocks: [],
  categories: [],
  profiles: [],
  currentProfileId: localStorage.getItem("vault_profile_id") ? Number(localStorage.getItem("vault_profile_id")) : null,
  grouped: true,
  groups: [],
  selectedIds: new Set(),
  filters: { q: "", category: "", district_id: "", block_id: "", is_duplicate: "", tag: "", is_favorite: false, sort: "title", search_mode: "basic", include_password: false },
  searchTimer: null,
};

/* ---------------- API helpers ---------------- */

async function api(path, options = {}) {
  const headers = { ...(options.headers || {}) };
  if (state.token) headers["Authorization"] = `Bearer ${state.token}`;
  const resp = await fetch(path, { ...options, headers });
  if (resp.status === 401 && !options.skipAuthError) {
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
  tag: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M3 12V4a1 1 0 0 1 1-1h8l9 9-9 9-9-9Z"/><circle cx="7.5" cy="7.5" r="1.5"/></svg>',
  profile: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="8" r="4"/><path d="M6 21v-2a4 4 0 0 1 4-4h4a4 4 0 0 1 4 4v2"/></svg>',
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

// Category pill colors (by slug/name) — fallback to gray
const CATEGORY_PILL_COLORS = {
  email: "cyan", banking: "amber", social: "violet", shopping: "green",
  work: "violet", entertainment: "cyan", other: "gray",
  education: "blue", finance: "amber", government: "red", health: "red", travel: "orange"
};

function pillColorFor(cat) {
  const key = String(cat || "").toLowerCase().replace(/\s+/g, "-");
  return CATEGORY_PILL_COLORS[key] || "gray";
}

function pillFor(cat) {
  const cls = pillColorFor(cat);
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
        skipAuthError: true,
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
        <button class="nav-item ${activeNav === "profiles" ? "active" : ""}" data-nav="profiles">${ICONS.profile}<span>Profiles</span></button>
        <button class="nav-item ${activeNav === "users" ? "active" : ""}" data-nav="users">${ICONS.users}<span>Users</span></button>
        <button class="nav-item ${activeNav === "audit" ? "active" : ""}" data-nav="audit">${ICONS.log}<span>Audit log</span></button>
        <button class="nav-item ${activeNav === "districts" ? "active" : ""}" data-nav="districts">${ICONS.box}<span>Districts</span></button>
        <button class="nav-item ${activeNav === "categories" ? "active" : ""}" data-nav="categories">${ICONS.tag}<span>Categories</span></button>
        <div class="sidebar-footer">
          <div class="user-chip">
            <div class="avatar">${escapeHtml((state.user?.username || "?").slice(0, 2))}</div>
            <div class="meta">
              <div class="name">${escapeHtml(state.user?.username)}</div>
              <div class="role">Admin</div>
            </div>
            <button class="icon-btn" id="settings-btn" title="Settings">${ICONS.edit}</button>
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
  const settingsBtn = document.getElementById("settings-btn");
  if (settingsBtn) settingsBtn.addEventListener("click", openSettingsModal);
}

function logout(silent = true) {
  state.token = null;
  state.user = null;
  localStorage.removeItem("vault_token");
  localStorage.removeItem("vault_user");
  location.hash = "#/login";
  if (!silent) toast("Signed out");
}

async function openSettingsModal() {
  try {
    const user = await api("/api/auth/me");
    const currentProfile = state.profiles.find((p) => p.id === state.currentProfileId);
    openModal(`
      <div class="modal-head">
        <div class="modal-title">Settings</div>
        <button class="modal-close" data-close="1">×</button>
      </div>
      ${currentProfile ? `<div class="field"><label>Current profile</label><div style="display:flex;align-items:center;gap:8px"><span style="font-weight:600">${escapeHtml(currentProfile.name)}</span><button class="btn btn-ghost" id="switch-profile-btn">Switch</button></div></div>` : ""}
      <div class="field">
        <label style="display:flex;align-items:center;gap:8px;font-weight:normal">
          <input type="checkbox" id="search-include-password" ${user.search_include_password ? "checked" : ""} />
          <span>Include passwords in smart search</span>
        </label>
        <div style="font-size:12px;color:var(--text-3);margin-top:4px">When enabled, smart search will also match against decrypted passwords. Requires Smart Search toggle in Vault.</div>
      </div>
      <div class="modal-foot">
        <button class="btn btn-ghost" data-close="1">Cancel</button>
        <button class="btn btn-primary" id="save-settings">Save</button>
      </div>
    `);
    document.getElementById("save-settings").addEventListener("click", async () => {
      const includePassword = document.getElementById("search-include-password").checked;
      try {
        await api("/api/users/me", {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ search_include_password: includePassword }),
        });
        state.user.search_include_password = includePassword;
        localStorage.setItem("vault_user", JSON.stringify(state.user));
        toast("Settings saved", "success");
        closeModal();
      } catch (ex) {
        toast(ex.message, "error");
      }
    });
    const switchBtn = document.getElementById("switch-profile-btn");
    if (switchBtn) switchBtn.addEventListener("click", () => { state.currentProfileId = null; localStorage.removeItem("vault_profile_id"); closeModal(); location.hash = "#/profiles"; });
  } catch (ex) {
    toast(ex.message, "error");
  }
}

/* ---------------- Vault view ---------------- */

async function loadEntries() {
  const params = new URLSearchParams();
  if (state.filters.q) params.set("q", state.filters.q);
  if (state.filters.search_mode) params.set("search_mode", state.filters.search_mode);
  if (state.filters.include_password) params.set("include_password", "true");
  if (state.filters.category) params.set("category", state.filters.category);
  if (state.filters.district_id) params.set("district_id", state.filters.district_id);
  if (state.filters.block_id) params.set("block_id", state.filters.block_id);
  if (state.filters.is_duplicate) params.set("is_duplicate", state.filters.is_duplicate);
  if (state.filters.tag) params.set("tag", state.filters.tag);
  if (state.filters.is_favorite) params.set("is_favorite", "true");
  if (state.filters.sort && state.filters.sort !== "title") params.set("sort", state.filters.sort);
  if (state.currentProfileId) params.set("profile_id", state.currentProfileId);
  try {
    state.entries = await api(`/api/entries?${params}`);
  } catch (e) {
    console.error("loadEntries failed", e);
    toast(e.message || "Failed to load entries", "error");
    state.entries = [];
  }
}

async function refreshCurrentView() {
  if (state.grouped) {
    await loadGroups();
    renderGrouped();
  } else {
    renderEntryRows();
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
      <label style="display:flex;align-items:center;gap:6px;font-size:13px" title="Use PostgreSQL full-text search (username, notes, password*)">
        <input type="checkbox" id="smart-search-toggle" ${state.filters.search_mode === "smart" ? "checked" : ""} />
        <span>Smart</span>
      </label>
      <input id="tag-search" placeholder="Tag" value="${escapeHtml(state.filters.tag)}" style="max-width:140px" class="input" />
      <button class="btn btn-primary" id="import-btn">${ICONS.up} Import</button>
      <button class="btn btn-ghost" id="export-csv-btn">${ICONS.down} CSV</button>
      <button class="btn btn-ghost" id="export-xlsx-btn">${ICONS.down} Excel</button>
      <button class="btn btn-ghost" id="delete-all-btn" style="color:#F87171">${ICONS.trash} Delete all</button>
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
    <div id="bulk-bar" style="display:${state.selectedIds.size?"flex":"none"};gap:8px;align-items:center;margin:12px 0;padding:10px;background:var(--surface-2);border-radius:10px;flex-wrap:wrap">
      <span>${state.selectedIds.size} selected</span>
      <select id="bulk-district" class="input" style="max-width:140px"><option value="">District</option>${state.districts.map(d=>`<option value="${d.id}">${escapeHtml(d.name)}</option>`).join("")}</select>
      <select id="bulk-block" class="input" style="max-width:140px"><option value="">Block</option>${state.blocks.map(b=>`<option value="${b.id}">${escapeHtml(b.name)}</option>`).join("")}</select>
      <select id="bulk-cat" class="input" style="max-width:180px"><option value="">Category</option>${catFlat().map(c=>`<option value="${c.id}">${escapeHtml(c.name)}${c.parent_id?" (sub)":""}</option>`).join("")}</select>
      <input id="bulk-new-cat" class="input" style="max-width:170px" placeholder="or new category…" />
      <button class="btn btn-primary" id="bulk-assign">Assign</button>
      <select id="bulk-profile" class="input" style="max-width:160px"><option value="">Profile</option>${state.profiles.map(p=>`<option value="${p.id}">${escapeHtml(p.name)}</option>`).join("")}<option value="none">— No profile</option></select>
      <button class="btn btn-ghost" id="bulk-delete" style="color:#F87171">${ICONS.trash} Delete</button>
      <button class="btn btn-ghost" id="bulk-clear">Clear</button>
    </div>

    <div style="display:flex;gap:10px;margin-bottom:12px"><label style="display:flex;align-items:center;gap:6px;font-size:13px"><input type="checkbox" id="grouped-toggle" ${state.grouped?"checked":""}/> Grouped by host (collapse duplicates)</label><span style="font-size:12px;color:var(--text-3)">registrable domain merges subdomains — admin can Split</span></div>
    <div class="chip-row">
      <button class="chip ${!state.filters.category ? "active" : ""}" data-cat="">All</button>
      ${state.categories.flatMap(c => [c, ...(c.children || [])]).map(c => `<button class="chip ${state.filters.category === c.name ? "active" : ""}" data-cat="${escapeHtml(c.name)}">${escapeHtml(c.name)}</button>`).join("")}
    </div>

    <div id="grouped-wrap" style="display:${state.grouped?"block":"none"}"></div>
    <div class="table-wrap" id="flat-wrap" style="display:${state.grouped?"none":"block"}">
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
  if (state.grouped) renderGrouped();
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

async function renderGrouped() {
  const wrap = document.getElementById("grouped-wrap");
  if (!wrap) return;
  if (!state.grouped) { wrap.style.display="none"; document.getElementById("flat-wrap").style.display="block"; return; }
  wrap.style.display="block"; document.getElementById("flat-wrap").style.display="none";
  if (!state.groups.length) { wrap.innerHTML=`<div class="empty-state"><div class="big">🗂️</div><h3>No groups</h3><div>Try different filters</div></div>`; return; }
  wrap.innerHTML = state.groups.map(g=>`
    <div style="background:var(--surface-1);border:1px solid var(--border);border-radius:14px;margin-bottom:12px;overflow:hidden">
      <div style="display:flex;align-items:center;gap:12px;padding:14px 18px;cursor:pointer" data-group="${g.registrable_domain}">
        <div style="flex:1">
          <div style="font-weight:600">${escapeHtml(g.display_name || g.registrable_domain)} <span style="font-size:12px;color:var(--text-3);font-weight:400;margin-left:6px">${escapeHtml(g.registrable_domain)}</span> <span class="pill violet" style="margin-left:8px">${g.count} ${g.count===1?"entry":"entries"}</span> <span class="pill ${g.effective_category==="Other"?"gray":"cyan"}">${escapeHtml(g.effective_category||"Other")}</span></div>
          <div style="font-size:12px;color:var(--text-3)">${[...new Set(g.exact_hosts)].map(h=>escapeHtml(h)).join(", ")} · ${[...new Set(g.sample_titles)].map(t=>escapeHtml(t)).join(", ")}</div>
        </div>
        <div style="display:flex;gap:6px"><button class="mini-btn" data-expand="${g.registrable_domain}" title="Expand">${ICONS.eye}</button><button class="mini-btn" data-cat-group="${g.registrable_domain}" title="Set category">${ICONS.edit}</button></div>
      </div>
      <div id="group-${g.registrable_domain.replace(/[^a-z0-9]/g,"_")}" style="display:none;border-top:1px solid var(--border)"></div>
    </div>`).join("");
  wrap.querySelectorAll("[data-expand]").forEach(b=> b.addEventListener("click", async(e)=>{
    e.stopPropagation(); const domain=b.dataset.expand; const key=domain.replace(/[^a-z0-9]/g,"_"); const el=document.getElementById("group-"+key);
    if(el.style.display==="none"){
      // load entries for this host
      const entries = await api(`/api/entries?registrable_domain=${encodeURIComponent(domain)}`);
      el.innerHTML=`<div style="padding:8px"><table style="min-width:0"><thead><tr><th>Name</th><th>Username</th><th>Updated</th><th style="min-width:110px"></th></tr></thead><tbody>`+entries.map(en=>`<tr><td class="strong">${escapeHtml(en.title)} ${en.is_duplicate?`<span class="pill red">dup</span>`:""}</td><td>${escapeHtml(en.username||"—")}</td><td>${timeAgo(en.updated_at)}</td><td><div class="cell-actions"><button class="mini-btn" data-view="${en.id}">${ICONS.eye}</button><button class="mini-btn" data-edit="${en.id}">${ICONS.edit}</button></div></td></tr>`).join("")+`</tbody></table></div>`;
      el.style.display="block";
      el.querySelectorAll("[data-view]").forEach(x=> x.addEventListener("click", ()=> viewEntry(Number(x.dataset.view))));
      el.querySelectorAll("[data-edit]").forEach(x=> x.addEventListener("click", ()=> openEntryForm(Number(x.dataset.edit))));
    } else el.style.display="none";
  }));
  wrap.querySelectorAll("[data-cat-group]").forEach(b=> b.addEventListener("click", ()=>{
    const domain=b.dataset.catGroup; const grp=state.groups.find(g=>g.registrable_domain===domain);
    openGroupCategoryModal(domain, grp);
  }));
}
function openGroupCategoryModal(domain, grp){
  const cats = state.categories.flatMap(c=> [c, ...(c.children||[]) ]);
  const dn = grp?.display_name || domain;
  openModal(`<div class="modal-head"><div class="modal-title">Set category for ${escapeHtml(dn)}</div><button class="modal-close" data-close="1">×</button></div><div class="field"><label>Category (global, admin only)</label><select class="input" id="g-cat"><option value="">— Keep —</option>${cats.map(c=>`<option value="${c.id}">${escapeHtml(c.name)}${c.parent_id?" (sub)":""}</option>`).join("")}</select></div><div class="field"><label>Or create new category</label><input class="input" id="g-new-cat" placeholder="New category name…" /></div><div style="font-size:12px;color:var(--text-3)">Applies to all ${grp?grp.count:""} entries under ${escapeHtml(domain)} (all users).</div><div class="modal-foot"><button class="btn btn-ghost" data-close="1">Cancel</button><button class="btn btn-primary" id="g-save">Save</button></div>`);
  document.getElementById("g-save").addEventListener("click", async()=>{
    try{
      let cid=document.getElementById("g-cat").value?Number(document.getElementById("g-cat").value):null;
      const newName=(document.getElementById("g-new-cat").value||"").trim();
      if(newName){
        const created=await api("/api/categories",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({name:newName,parent_id:null})});
        cid=created.id; toast(`Category "${newName}" created`,"success");
        await loadCategories();
      }
      if(!cid) return toast("Choose or create a category","error");
      // bulk assign all entries in group to category
      const entryIds = grp.entry_ids;
      await api(`/api/entries/bulk-assign?category_id=${cid}`, {method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify(entryIds)});
      toast(`Updated ${entryIds.length} entries to category`,"success"); closeModal(); await loadGroups(); renderGrouped();
    }catch(e){ toast(e.message,"error"); }
  });
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
  body.querySelectorAll(".row-check").forEach((c)=> c.addEventListener("change", (e)=>{ const id=Number(e.target.dataset.id); if(e.target.checked) state.selectedIds.add(id); else state.selectedIds.delete(id); const bar=document.getElementById("bulk-bar"); bar.style.display=state.selectedIds.size?"flex":"none"; const cnt=bar.querySelector("span"); if(cnt) cnt.textContent=state.selectedIds.size+" selected"; }));

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
  const smartSearchToggle = document.getElementById("smart-search-toggle");
  search.addEventListener("input", debounce(async () => {
    state.filters.q = search.value.trim();
    await loadEntries();
    refreshCurrentView();
  }, 280));
  if (smartSearchToggle) smartSearchToggle.addEventListener("change", async () => {
    state.filters.search_mode = smartSearchToggle.checked ? "smart" : "basic";
    await loadEntries();
    refreshCurrentView();
  });
  if(tagSearch) tagSearch.addEventListener("input", debounce(async()=>{ state.filters.tag=tagSearch.value.trim(); await loadEntries(); refreshCurrentView();},300));
  if(districtSel) districtSel.addEventListener("change", async()=>{ state.filters.district_id=districtSel.value; state.filters.block_id=""; await loadEntries(); renderVault(); });
  if(blockSel) blockSel.addEventListener("change", async()=>{ state.filters.block_id=blockSel.value; await loadEntries(); refreshCurrentView(); });
  if(dupChk) dupChk.addEventListener("change", async()=>{ state.filters.is_duplicate=dupChk.checked?"true":""; await loadEntries(); refreshCurrentView(); });
  if(favChk) favChk.addEventListener("change", async()=>{ state.filters.is_favorite=favChk.checked; await loadEntries(); refreshCurrentView(); });
  if(sortSel) sortSel.addEventListener("change", async()=>{ state.filters.sort=sortSel.value; await loadEntries(); refreshCurrentView(); });
  if(clearBtn) clearBtn.addEventListener("click", async()=>{ state.filters={q:"",search_mode:"basic",include_password:false,category:"",district_id:"",block_id:"",is_duplicate:"",tag:"",is_favorite:false,sort:"title"}; await loadEntries(); if(state.grouped) await loadGroups(); renderVault(); });
  const groupedToggle=document.getElementById("grouped-toggle"); if(groupedToggle) groupedToggle.addEventListener("change", async()=>{ state.grouped=groupedToggle.checked; if(state.grouped) await loadGroups(); renderGrouped(); document.getElementById("flat-wrap").style.display=state.grouped?"none":"block"; document.getElementById("grouped-wrap").style.display=state.grouped?"block":"none"; if(!state.grouped) renderEntryRows(); });
  const bulkDistrict=document.getElementById("bulk-district"); const bulkBlock=document.getElementById("bulk-block"); const bulkCat=document.getElementById("bulk-cat"); const bulkNewCat=document.getElementById("bulk-new-cat"); const bulkAssign=document.getElementById("bulk-assign"); const bulkProfile=document.getElementById("bulk-profile"); const bulkDelete=document.getElementById("bulk-delete"); const bulkClear=document.getElementById("bulk-clear"); const selectAll=document.getElementById("select-all");
  if(bulkAssign) bulkAssign.addEventListener("click", async()=>{
    const ids=[...state.selectedIds]; if(!ids.length) return;
    try{
      let cid=bulkCat.value?Number(bulkCat.value):null;
      const did=bulkDistrict.value?Number(bulkDistrict.value):null; const bid=bulkBlock.value?Number(bulkBlock.value):null;
      const newName=(bulkNewCat?.value||"").trim();
      if(newName){
        const created=await api("/api/categories",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({name:newName,parent_id:null})});
        cid=created.id; toast(`Category "${newName}" created`,"success");
        await loadCategories();
        state.selectedIds=new Set(ids);
        renderVault();
      }
      const qp=[]; if(did)qp.push(`district_id=${did}`); if(bid)qp.push(`block_id=${bid}`); if(cid)qp.push(`category_id=${cid}`);
      if(!qp.length) return toast("Choose district, block or category","error");
      await api(`/api/entries/bulk-assign?${qp.join("&")}`, {method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify(ids)});
      toast(`Assigned ${ids.length} entries`,"success"); state.selectedIds.clear(); await loadEntries(); refreshCurrentView(); document.getElementById("bulk-bar").style.display="none";
    }catch(e){toast(e.message,"error");}
  });
  if(bulkProfile) bulkProfile.addEventListener("change", async()=>{
    const ids=[...state.selectedIds]; if(!ids.length) return toast("Select entries first","info");
    const val=bulkProfile.value;
    const pid=val==="none"?null:val?Number(val):null;
    if(pid===null && val==="") return;
    try{
      const qp=pid!==null?`?profile_id=${pid}`:"";
      await api(`/api/entries/bulk-assign-profile${qp}`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(ids)});
      toast(`Assigned ${ids.length} entries to ${val==="none"?"no profile":state.profiles.find(p=>p.id===pid)?.name||"profile"}`,"success");
      bulkProfile.value=""; state.selectedIds.clear(); await loadEntries(); if(state.grouped) await loadGroups(); renderVault();
    }catch(e){toast(e.message,"error");}
  });
  if(bulkDelete) bulkDelete.addEventListener("click", async()=>{
    const ids=[...state.selectedIds]; if(!ids.length) return;
    if(!confirm(`Delete ${ids.length} entries? This cannot be undone.`)) return;
    try{
      await api("/api/entries/bulk-delete",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(ids)});
      toast(`Deleted ${ids.length} entries`,"success"); state.selectedIds.clear(); await loadEntries(); if(state.grouped) await loadGroups(); renderVault();
    }catch(e){toast(e.message,"error");}
  });
  if(bulkClear) bulkClear.addEventListener("click", ()=>{ state.selectedIds.clear(); renderEntryRows(); document.getElementById("bulk-bar").style.display="none";});
  if(selectAll) selectAll.addEventListener("change", (e)=>{ if(e.target.checked){ state.entries.forEach(en=>state.selectedIds.add(en.id));} else state.selectedIds.clear(); renderEntryRows(); const cnt=document.querySelector("#bulk-bar span"); if(cnt) cnt.textContent=state.selectedIds.size+" selected"; });


  document.querySelectorAll("[data-cat]").forEach((chip) => {
    chip.addEventListener("click", async () => {
      state.filters.category = chip.dataset.cat;
      document.querySelectorAll("[data-cat]").forEach((c) => c.classList.toggle("active", c === chip));
      await loadEntries();
      refreshCurrentView();
    });
  });

  document.getElementById("add-btn").addEventListener("click", () => openEntryForm());
  document.getElementById("import-btn").addEventListener("click", () => openImportWizard());
  document.getElementById("export-csv-btn").addEventListener("click", () => exportVault("csv"));
  document.getElementById("export-xlsx-btn").addEventListener("click", () => exportVault("xlsx"));
  document.getElementById("delete-all-btn").addEventListener("click", async()=>{
    const count = state.entries.length;
    if(!count) return toast("No entries to delete","info");
    if(!confirm(`Delete ALL ${count} entries? This cannot be undone.`)) return;
    try{
      const res = await api("/api/entries/all",{method:"DELETE"});
      toast(`Deleted ${res.deleted} entries`,"success"); state.selectedIds.clear(); await loadEntries(); if(state.grouped) await loadGroups(); renderVault();
    }catch(e){toast(e.message,"error");}
  });
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
      <div class="field" style="display:flex;gap:6px;flex-wrap:wrap">${e.district_name?`<span class="pill violet">${escapeHtml(e.district_name)}</span>`:""} ${e.block_name?`<span class="pill cyan">${escapeHtml(e.block_name)}</span>`:""} ${e.is_duplicate?`<span class="pill red">duplicate</span>`:""} <span class="pill cyan">${escapeHtml(e.effective_category||e.category)}</span>${e.effective_subcategory?`<span class="pill violet">${escapeHtml(e.effective_subcategory)}</span>`:""} ${(e.tags||[]).map(t=>`<span class="pill green">${escapeHtml(t)}</span>`).join("")} <span class="pill gray">${escapeHtml(e.registrable_domain||hostOf(e.url))}</span></div>
      <div class="field" style="display:flex;gap:8px"><select class="input" id="my-cat" style="flex:1"><option value="">My category (private)</option>${state.categories.map(c=>`<option value="${c.id}">${escapeHtml(c.name)}</option>`).join("")}</select><button class="btn btn-ghost" id="my-cat-save">Set my</button><button class="btn btn-ghost" id="global-cat-save">Set global (admin)</button></div>
      <label style="display:flex;align-items:center;gap:6px;font-size:12px;color:var(--text-3)"><input type="checkbox" id="apply-to-site" /> Apply global category to ALL entries with same site (${escapeHtml(e.registrable_domain || e.host || "this domain")})</label>
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
    const myCatBtn=document.getElementById("my-cat-save"); if(myCatBtn) myCatBtn.addEventListener("click", async()=>{ const v=document.getElementById("my-cat").value; if(!v) return toast("Choose category","error"); try{ await api(`/api/entries/${e.id}/my-category`,{method:"PUT", headers:{"Content-Type":"application/json"}, body: JSON.stringify({category_id:Number(v)})}); toast("My category saved (private)","success"); closeModal(); viewEntry(e.id);}catch(ex){toast(ex.message,"error");}});
    const gloBtn=document.getElementById("global-cat-save"); if(gloBtn) gloBtn.addEventListener("click", async()=>{ const v=document.getElementById("my-cat").value; if(!v) return toast("Choose category","error"); const applyGroup=document.getElementById("apply-to-site")?.checked; try{ const r=await api(`/api/entries/${e.id}/category${applyGroup?"?apply_to_group=true":""}`,{method:"PUT", headers:{"Content-Type":"application/json"}, body: JSON.stringify({category_id:Number(v)})}); toast(applyGroup?`Applied to ${r.updated||1} entries (whole site)`:"Global category updated","success"); closeModal(); if(state.grouped){await loadGroups(); renderGrouped();} viewEntry(e.id);}catch(ex){toast(ex.message,"error");}});
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
        <div class="field"><label>Category (legacy)</label>
          <select class="input" id="f-category"><option value="">— None</option>${state.categories.flatMap(c => [c, ...(c.children || [])]).map(c => `<option value="${escapeHtml(c.name)}" ${existing?.category === c.name ? "selected" : ""}>${escapeHtml(c.name)}</option>`).join("")}</select>
        </div>
        <div class="field"><label>Smart category (global, admin)</label><select class="input" id="f-smart-cat"><option value="">— None</option>${state.categories.map(c=>`<option value="${c.id}" ${existing?.smart_category_id===c.id?"selected":""}>${escapeHtml(c.name)}</option>`).join("")}${state.categories.flatMap(c=> c.children||[]).map(sc=>`<option value="${sc.id}" ${existing?.smart_subcategory_id===sc.id?"selected":""}>↳ ${escapeHtml(sc.name)}</option>`).join("")}</select></div>
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
      smart_category_id: document.getElementById("f-smart-cat")?.value?Number(document.getElementById("f-smart-cat").value):null,
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
      <div style="display:flex;gap:10px;margin:12px 0"><select id="wiz-profile" class="input" style="flex:1"><option value="">— Assign profile (optional)</option>${state.profiles.map(p=>`<option value="${p.id}">${escapeHtml(p.name)}</option>`).join("")}</select></div>
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
        <div class="preview-meta" style="margin-top:12px"><strong>Host groups (collapsed)</strong> — registrable domain merges subdomains</div>
        <div style="display:flex;flex-wrap:wrap;gap:8px;margin:8px 0">${p.host_groups.map(g=>`<span class="pill violet">${escapeHtml(g.registrable_domain)} (${g.count})</span>`).join("")||"<span class=\"pill gray\">—</span>"}</div>
        <div class="preview-meta"><strong>Smart categories (AI ${p.smart_groups.some(x=>x.is_ai)?"✨":"rule"})</strong> — permit to apply</div>
        <div style="display:flex;flex-wrap:wrap;gap:8px;margin:8px 0">${p.smart_groups.map(g=>`<span class="pill cyan">${escapeHtml(g.registrable_domain)} → ${escapeHtml(g.proposed_category)} ${g.is_ai?"✨":""}</span>`).join("")||"<span class=\"pill gray\">—</span>"}</div>
        <div style="display:flex;gap:8px;margin:12px 0"><label style="display:flex;align-items:center;gap:6px;font-size:13px"><input type="checkbox" id="wiz-permit" /> Permit smart categories</label><span style="font-size:12px;color:var(--text-3)">If unchecked, imports with original categories (normal collapsed)</span></div>
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
      const did=document.getElementById("wiz-district")?.value; const bid=document.getElementById("wiz-block")?.value; const pid=document.getElementById("wiz-profile")?.value; const dedup=document.getElementById("wiz-dedup")?.value||"none"; const skip=document.getElementById("wiz-skip")?.checked; const permit=document.getElementById("wiz-permit")?.checked; if(did) form.append("district_id", did); if(bid) form.append("block_id", bid); if(pid) form.append("profile_id", pid); form.append("dedup_mode", dedup); form.append("skip_duplicates", skip?"true":"false"); form.append("permit_smart", permit?"true":"false");
      try {
        const res = await api("/api/import/confirm", { method: "POST", body: form });
        closeModal();
        toast(`Imported ${res.imported}, skipped ${res.skipped_duplicates} duplicate${res.skipped_duplicates === 1 ? "" : "s"}${res.failed ? `, ${res.failed} failed` : ""}`, res.failed ? "info" : "success");
        if (res.failed && Array.isArray(res.errors) && res.errors.length) {
          openModal(`
            <div class="modal-head"><div class="modal-title">Import problems</div><button class="modal-close" data-close="1">×</button></div>
            <div>
              <p style="margin:0 0 12px;color:var(--text-2);font-size:13.5px">${res.failed} row${res.failed === 1 ? "" : "s"} could not be imported. First ${res.errors.length} reason${res.errors.length === 1 ? "" : "s"}:</p>
              <ul style="margin:0;padding-left:18px;display:flex;flex-direction:column;gap:8px">
                ${res.errors.map((er) => `<li style="font-size:13px;color:var(--text-1);word-break:break-word">${escapeHtml(er)}</li>`).join("")}
              </ul>
            </div>
            <div class="modal-foot"><button class="btn btn-primary" data-close="1">Understood</button></div>`);
        }
        await loadEntries();
        if (state.grouped) await loadGroups();
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
async function loadCategories() {
  try { state.categories = await api("/api/categories"); } catch(e){ state.categories=[]; }
}
async function loadGroups() {
  try {
    const params = new URLSearchParams();
    if (state.filters.q) params.set("q", state.filters.q);
    if (state.filters.search_mode) params.set("search_mode", state.filters.search_mode);
    if (state.filters.category) params.set("category", state.filters.category);
    if (state.filters.district_id) params.set("district_id", state.filters.district_id);
    if (state.filters.block_id) params.set("block_id", state.filters.block_id);
    if (state.filters.is_duplicate) params.set("is_duplicate", state.filters.is_duplicate);
    if (state.filters.tag) params.set("tag", state.filters.tag);
    if (state.filters.is_favorite) params.set("is_favorite", "true");
    if (state.currentProfileId) params.set("profile_id", state.currentProfileId);
    state.groups = await api(`/api/entries/groups?${params}`);
  } catch(e){ state.groups=[]; }
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

/* ---------------- Categories (admin) ---------------- */

function catFlat() {
  return state.categories.flatMap((c) => [c, ...(c.children || [])]);
}

async function renderCategories() {
  document.getElementById("app").innerHTML = shell(
    "Categories",
    "Create and manage custom categories. Assign them in bulk from the Vault.",
    `<div class="toolbar"><button class="btn btn-primary" id="add-category">+ Category</button></div>
     <div class="table-wrap"><table><thead><tr><th>Name</th><th>Parent</th><th>Entries</th><th>Type</th><th style="min-width:110px"></th></tr></thead><tbody id="category-body"></tbody></table></div>`,
    "categories"
  );
  bindShell();
  const body = document.getElementById("category-body");
  const flat = catFlat();
  body.innerHTML = flat.map((c) => `
    <tr>
      <td class="strong">${c.parent_id ? "&nbsp;&nbsp;↳ " : ""}${escapeHtml(c.name)}</td>
      <td>${escapeHtml(flat.find((p) => p.id === c.parent_id)?.name || "—")}</td>
      <td>${c.entry_count ?? 0}</td>
      <td>${c.is_system ? '<span class="pill gray">system</span>' : '<span class="pill cyan">custom</span>'}</td>
      <td><div class="cell-actions">
        ${c.is_system ? "" : `<button class="mini-btn" data-ren-cat="${c.id}" title="Rename">${ICONS.edit}</button><button class="mini-btn danger" data-del-cat="${c.id}" title="Delete">${ICONS.trash}</button>`}
      </div></td>
    </tr>`).join("") || '<tr><td colspan="5">No categories yet</td></tr>';
  body.querySelectorAll("[data-del-cat]").forEach((b) => b.addEventListener("click", async () => {
    try { await api(`/api/categories/${b.dataset.delCat}`, { method: "DELETE" }); toast("Category deleted", "success"); await loadCategories(); renderCategories(); }
    catch (e) { toast(e.message, "error"); }
  }));
  body.querySelectorAll("[data-ren-cat]").forEach((b) => b.addEventListener("click", () => {
    const c = flat.find((x) => x.id === Number(b.dataset.renCat));
    openModal(`<div class="modal-head"><div class="modal-title">Rename category</div><button class="modal-close" data-close="1">×</button></div>
      <div class="field"><label>Name</label><input class="input" id="ren-name" value="${escapeHtml(c.name)}" /></div>
      <div class="modal-foot"><button class="btn btn-ghost" data-close="1">Cancel</button><button class="btn btn-primary" id="ren-save">Save</button></div>`);
    document.getElementById("ren-save").addEventListener("click", async () => {
      const n = document.getElementById("ren-name").value.trim(); if (!n) return;
      try { await api(`/api/categories/${c.id}`, { method: "PUT", headers: {"Content-Type":"application/json"}, body: JSON.stringify({ name: n }) }); toast("Renamed", "success"); closeModal(); await loadCategories(); renderCategories(); }
      catch (e) { toast(e.message, "error"); }
    });
  }));
  document.getElementById("add-category").addEventListener("click", () => openCategoryCreateModal(async () => { await loadCategories(); renderCategories(); }));
}

function openCategoryCreateModal(onDone) {
  const roots = state.categories;
  openModal(`<div class="modal-head"><div class="modal-title">New category</div><button class="modal-close" data-close="1">×</button></div>
    <div class="field"><label>Name</label><input class="input" id="new-cat-name" placeholder="e.g. LokOS Portal" /></div>
    <div class="field"><label>Parent (optional)</label><select class="input" id="new-cat-parent"><option value="">— Top level —</option>${roots.map((c) => `<option value="${c.id}">${escapeHtml(c.name)}</option>`).join("")}</select></div>
    <div class="modal-foot"><button class="btn btn-ghost" data-close="1">Cancel</button><button class="btn btn-primary" id="new-cat-save">Create</button></div>`);
  document.getElementById("new-cat-save").addEventListener("click", async () => {
    const n = document.getElementById("new-cat-name").value.trim();
    if (!n) return toast("Enter a name", "error");
    const pid = document.getElementById("new-cat-parent").value;
    try {
      const created = await api("/api/categories", { method: "POST", headers: {"Content-Type":"application/json"}, body: JSON.stringify({ name: n, parent_id: pid ? Number(pid) : null }) });
      toast("Category created", "success"); closeModal();
      if (onDone) await onDone(created);
    } catch (e) { toast(e.message, "error"); }
  });
}

/* ---------------- Profile selector ---------------- */

async function loadProfiles() {
  try { state.profiles = await api("/api/profiles"); } catch (e) { state.profiles = []; }
}

function renderProfileSelector() {
  document.getElementById("app").innerHTML = `
    <div class="login-shell">
      <div class="login-card" style="max-width:520px">
        <div class="login-brand">
          <div class="brand-mark">◆</div>
          <div>
            <div class="login-title">Who's watching?</div>
            <div class="login-sub">Select a profile to continue</div>
          </div>
        </div>
        <div id="profile-grid" class="profile-grid">
          ${state.profiles.length === 0 ? '<div style="text-align:center;padding:24px 0;color:var(--text-3)">No profiles yet. Create one to get started.</div>' : ""}
        </div>
        <button class="btn btn-ghost btn-lg" id="create-profile-btn" style="width:100%;justify-content:center;margin-top:12px">${ICONS.plus} New profile</button>
      </div>
    </div>`;

  const grid = document.getElementById("profile-grid");
  state.profiles.forEach((p) => {
    const card = document.createElement("div");
    card.className = "profile-card";
    card.innerHTML = `
      <div class="profile-avatar">${p.avatar_url ? `<img src="${escapeHtml(p.avatar_url)}" alt="" />` : ICONS.profile}</div>
      <div class="profile-name">${escapeHtml(p.name)}</div>
      ${p.has_pin ? '<div class="profile-lock">🔒</div>' : ""}`;
    card.addEventListener("click", () => selectProfileInSpa(p));
    grid.appendChild(card);
  });

  document.getElementById("create-profile-btn").addEventListener("click", () => openCreateProfileModal(async () => {
    await loadProfiles();
    renderProfileSelector();
  }));
}

function selectProfileInSpa(profile) {
  if (profile.has_pin) {
    openModal(`
      <div class="modal-head"><div class="modal-title">Enter PIN</div><button class="modal-close" data-close="1">×</button></div>
      <div class="field"><label>PIN for ${escapeHtml(profile.name)}</label><input class="input" id="profile-pin" type="password" inputmode="numeric" placeholder="PIN" /></div>
      <div class="modal-foot"><button class="btn btn-ghost" data-close="1">Cancel</button><button class="btn btn-primary" id="profile-pin-ok">OK</button></div>
    `);
    document.getElementById("profile-pin-ok").addEventListener("click", async () => {
      const pin = document.getElementById("profile-pin").value;
      try {
        await api(`/api/profiles/${profile.id}/select`, { method: "POST", headers: {"Content-Type":"application/json"}, body: JSON.stringify({ pin }) });
        state.currentProfileId = profile.id;
        localStorage.setItem("vault_profile_id", profile.id);
        closeModal();
        if (location.hash === "#/vault") router(); else location.hash = "#/vault";
      } catch (e) { toast("Invalid PIN", "error"); }
    });
  } else {
    state.currentProfileId = profile.id;
    localStorage.setItem("vault_profile_id", profile.id);
    if (location.hash === "#/vault") router(); else location.hash = "#/vault";
  }
}

function openCreateProfileModal(onDone) {
  openModal(`
    <div class="modal-head"><div class="modal-title">New profile</div><button class="modal-close" data-close="1">×</button></div>
    <div class="field"><label>Name</label><input class="input" id="new-profile-name" placeholder="e.g. Personal" /></div>
    <div class="modal-foot"><button class="btn btn-ghost" data-close="1">Cancel</button><button class="btn btn-primary" id="new-profile-save">Create</button></div>
  `);
  document.getElementById("new-profile-save").addEventListener("click", async () => {
    const name = document.getElementById("new-profile-name").value.trim();
    if (!name) return toast("Enter a name", "error");
    try {
      await api("/api/profiles", { method: "POST", headers: {"Content-Type":"application/json"}, body: JSON.stringify({ name }) });
      toast("Profile created", "success"); closeModal();
      if (onDone) await onDone();
    } catch (e) { toast(e.message, "error"); }
  });
}

/* ---------------- Profiles management view ---------------- */

function renderProfiles() {
  document.getElementById("app").innerHTML = shell(
    "Profiles",
    "Manage profile access for your team.",
    `
    <div style="display:flex;justify-content:flex-end;margin-bottom:16px">
      <button class="btn btn-primary" id="add-profile">${ICONS.plus} New profile</button>
    </div>
    <div class="table-wrap">
      <table class="table" id="profiles-table">
        <thead><tr><th>Name</th><th>Users</th><th>PIN</th><th></th></tr></thead>
        <tbody id="profiles-body"></tbody>
      </table>
    </div>
    `,
    "profiles"
  );
  bindShell();
  const body = document.getElementById("profiles-body");
  body.innerHTML = state.profiles.map((p) => `
    <tr>
      <td style="font-weight:600">${escapeHtml(p.name)}</td>
      <td>${p.user_count}</td>
      <td>${p.has_pin ? '<span class="pill amber">set</span>' : '<span class="pill gray">none</span>'}</td>
      <td><div class="cell-actions">
        <button class="mini-btn" data-manage-users="${p.id}" title="Manage users">${ICONS.users}</button>
        <button class="mini-btn" data-del-profile="${p.id}" title="Delete">${ICONS.trash}</button>
      </div></td>
    </tr>`).join("") || '<tr><td colspan="4">No profiles yet</td></tr>';

  body.querySelectorAll("[data-manage-users]").forEach((b) => b.addEventListener("click", () => openManageProfileUsersModal(Number(b.dataset.manageUsers))));
  body.querySelectorAll("[data-del-profile]").forEach((b) => b.addEventListener("click", async () => {
    try { await api(`/api/profiles/${b.dataset.delProfile}`, { method: "DELETE" }); toast("Profile deleted", "success"); await loadProfiles(); renderProfiles(); }
    catch (e) { toast(e.message, "error"); }
  }));
  document.getElementById("add-profile").addEventListener("click", () => openCreateProfileModal(async () => { await loadProfiles(); renderProfiles(); }));
}

async function openManageProfileUsersModal(profileId) {
  const profile = state.profiles.find((p) => p.id === profileId);
  if (!profile) return;
  // Load all users for the assign dropdown
  const allUsers = state.users || [];
  openModal(`
    <div class="modal-head"><div class="modal-title">Users in "${escapeHtml(profile.name)}"</div><button class="modal-close" data-close="1">×</button></div>
    <div class="field">
      <label>Import passwords to this profile</label>
      <div style="display:flex;gap:8px">
        <input type="file" id="profile-import-file" accept=".csv,.xlsx,.xls,.json" style="display:none" />
        <button class="btn btn-primary" id="profile-import-btn">${ICONS.up} Import file</button>
        <span style="font-size:12px;color:var(--text-3);align-self:center">CSV, Excel, or JSON</span>
      </div>
    </div>
    <div class="field">
      <label>Add user</label>
      <div style="display:flex;gap:8px">
        <select class="input" id="assign-user-select" style="flex:1">
          ${allUsers.map((u) => `<option value="${u.id}">${escapeHtml(u.username)} (${u.role})</option>`).join("")}
        </select>
        <button class="btn btn-primary" id="assign-user-btn">Add</button>
      </div>
    </div>
    <div class="field">
      <label>Set PIN for yourself on this profile</label>
      <div style="display:flex;gap:8px">
        <input class="input" id="set-pin-input" type="password" inputmode="numeric" placeholder="4-8 digit PIN" style="flex:1" />
        <button class="btn btn-ghost" id="set-pin-btn">Set PIN</button>
      </div>
    </div>
    <div class="modal-foot"><button class="btn btn-ghost" data-close="1">Done</button></div>
  `);
  document.getElementById("assign-user-btn").addEventListener("click", async () => {
    const uid = document.getElementById("assign-user-select").value;
    try { await api(`/api/profiles/${profileId}/users`, { method: "POST", headers: {"Content-Type":"application/json"}, body: JSON.stringify({ user_id: Number(uid) }) }); toast("User added", "success"); await loadProfiles(); }
    catch (e) { toast(e.message, "error"); }
  });
  document.getElementById("profile-import-btn").addEventListener("click", () => document.getElementById("profile-import-file").click());
  document.getElementById("profile-import-file").addEventListener("change", async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    closeModal();
    toast(`Importing to profile "${profile.name}"…`, "info");
    const form = new FormData();
    form.append("file", file);
    form.append("profile_id", profileId);
    form.append("mapping", "{}");
    form.append("dedup_mode", "none");
    form.append("skip_duplicates", "false");
    form.append("permit_smart", "false");
    try {
      const res = await api("/api/import/confirm", { method: "POST", body: form });
      toast(`Imported ${res.imported} to "${profile.name}", skipped ${res.skipped_duplicates} duplicate${res.skipped_duplicates===1?"":"s"}${res.failed?`, ${res.failed} failed`:""}`, res.failed?"info":"success");
      await loadEntries(); if(state.grouped) await loadGroups(); renderVault();
    } catch (ex) { toast(ex.message, "error"); }
  });
  document.getElementById("set-pin-btn").addEventListener("click", async () => {
    const pin = document.getElementById("set-pin-input").value;
    if (!pin || pin.length < 4) return toast("PIN must be 4-8 digits", "error");
    try { await api(`/api/profiles/${profileId}/pin`, { method: "POST", headers: {"Content-Type":"application/json"}, body: JSON.stringify({ pin }) }); toast("PIN set", "success"); await loadProfiles(); }
    catch (e) { toast(e.message, "error"); }
  });
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

  // Load profiles and check if profile is needed (skip for admin)
  if (!route.startsWith("/profiles")) {
    await loadProfiles();
    if (state.profiles.length > 0 && !state.currentProfileId && state.user.role !== "admin") {
      return renderProfileSelector();
    }
  }

  if (route.startsWith("/vault")) {
    await Promise.allSettled([loadDistricts(), loadBlocks(), loadCategories()]);
    await loadEntries();
    if (state.grouped) await loadGroups();
    try {
      renderVault();
      renderEntryRows();
    } catch (e) {
      console.error("renderVault failed", e);
      document.getElementById("app").innerHTML = `<div style="padding:32px"><h3>Vault failed to load</h3><p>${escapeHtml(e.message)}</p><p><a href="#/login" class="btn btn-primary">Back to login</a></p></div>`;
    }
  } else if (route.startsWith("/profiles")) {
    await Promise.all([loadProfiles(), loadUsers()]);
    renderProfiles();
  } else if (route.startsWith("/users")) {
    await Promise.all([loadUsers(), loadAudit()]);
    renderUsers();
  } else if (route.startsWith("/audit")) {
    await Promise.all([loadUsers(), loadAudit()]);
    renderAudit();
  } else if (route.startsWith("/districts")) {
    await Promise.all([loadDistricts(), loadBlocks()]);
    renderDistricts();
  } else if (route.startsWith("/categories")) {
    await loadCategories();
    renderCategories();
  }
}

window.addEventListener("hashchange", router);
router();
