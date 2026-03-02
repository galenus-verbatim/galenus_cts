const DB_URL = "/static/search-index.sqlite";

let db = null;

function stripDiacritics(str) {
  return str
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase();
}

/**
 * Build a safe FTS5 query string from user input.
 * - Single word  → plain token
 * - Multiple words → phrase query "word1 word2 …"
 * FTS5 special characters are removed before wrapping.
 */
function buildFtsQuery(raw) {
  const normalized = stripDiacritics(raw.trim());
  if (!normalized) return null;
  // Strip FTS5 operators/punctuation that would cause parse errors
  const sanitized = normalized.replace(/["()*^]/g, "").trim();
  if (!sanitized) return null;
  const words = sanitized.split(/\s+/).filter(Boolean);
  if (words.length === 0) return null;
  return words.length === 1 ? words[0] : `"${words.join(" ")}"`;
}

async function loadDatabase() {
  const statusEl = document.getElementById("search-status");
  statusEl.textContent = "Chargement de l'index…";

  const SQL = await initSqlJs({
    locateFile: (filename) =>
      `https://cdn.jsdelivr.net/npm/sql.js@1.10.3/dist/${filename}`,
  });

  const response = await fetch(DB_URL);
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  const buffer = await response.arrayBuffer();
  db = new SQL.Database(new Uint8Array(buffer));

  statusEl.textContent = "";
  const input = document.getElementById("search-input");
  input.disabled = false;
  input.focus();
}

function renderResults(rows) {
  const resultsEl = document.getElementById("search-results");
  const countEl = document.getElementById("search-count");

  if (rows.length === 0) {
    countEl.textContent = "0 résultat";
    resultsEl.innerHTML = '<p class="no-results">Aucun résultat.</p>';
    return;
  }

  const label =
    rows.length === 50
      ? "50+ résultats"
      : `${rows.length} résultat${rows.length !== 1 ? "s" : ""}`;
  countEl.textContent = label;

  resultsEl.innerHTML = rows
    .map((row) => {
      const passage = row.urn.split(":").pop();
      const langLabel = row.language === "grc" ? "grec" : "latin";
      return `<div class="search-result">
  <a href="/${row.urn}" class="result-link">${row.title}</a>
  <span class="result-meta">${langLabel} · ${passage}</span>
</div>`;
    })
    .join("");
}

function runSearch(query) {
  if (!db) return;

  const ftsQuery = buildFtsQuery(query);
  const resultsEl = document.getElementById("search-results");
  const countEl = document.getElementById("search-count");

  if (!ftsQuery) {
    resultsEl.innerHTML = "";
    countEl.textContent = "";
    return;
  }

  try {
    const stmt = db.prepare(`
      SELECT m.urn, m.language, m.title, m.location
      FROM textpart_meta m
      JOIN (SELECT rowid FROM search_fts WHERE search_fts MATCH ?) AS fts
        ON m.id = fts.rowid
      LIMIT 50
    `);
    stmt.bind([ftsQuery]);
    const rows = [];
    while (stmt.step()) rows.push(stmt.getAsObject());
    stmt.free();
    renderResults(rows);
  } catch (err) {
    console.error("Search error:", err);
    countEl.textContent = "";
    resultsEl.innerHTML = '<p class="search-error">Requête invalide.</p>';
  }
}

let debounceTimer;

document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("search-input").addEventListener("input", (e) => {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => runSearch(e.target.value), 300);
  });

  loadDatabase().catch((err) => {
    document.getElementById("search-status").textContent =
      `Erreur : ${err.message}`;
  });
});
