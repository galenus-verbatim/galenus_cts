const BASE_URL = "https://api.zotero.org";
const ZOTERO_API_VERSION = "3";

const COLLECTION_IDS_TO_NAMES = {
  "9QP457XQ": "Editiones criticae",
  XWUKKHRC: "Editiones verbatim",
  ZTP7ASC3: "Editiones veterae",
  EEF8L3QT: "Galeni et Pseudo-Galeni opera",
  DTQ8XZKP: "Libri ad Galenum pertinentes",
  "2XYEX7QT": "Translationes recentiores",
  J4EMVD4V: "Translationes verbatim",
};

const COLLECTION_NAMES_TO_IDS = Object.keys(COLLECTION_IDS_TO_NAMES).reduce(
  (obj, key) => {
    obj[COLLECTION_IDS_TO_NAMES[key]] = key;

    return obj;
  },
  {},
);

export async function fetchOpera(tags = []) {
  const path = "groups/4571007/collections/EEF8L3QT/items";
  let url = `${BASE_URL}/${path}?limit=100`;

  if (tags.length > 0) {
    url += `&tag=${tags}`;
  }

  const headers = { "Zotero-API-Version": ZOTERO_API_VERSION };
  const response = await fetch(url, { headers });
  const data = await response.json();

  return data;
}

// ignoreDuplicates is accepted for callers that pass it explicitly, but
// deduplication is always driven by the ignorer-doublons checkbox so that
// gommette-triggered re-filters also respect the current setting.
export async function filterEditions(ignoreDuplicates = false) {
  const gommettes = Array.from(
    document.querySelectorAll(".gommette:checked"),
  ).map((cb) => cb.value);

  const tbody = document.querySelector("#editions-table tbody");
  if (!tbody) return;

  // First pass: filter visible rows by gommette tags
  if (gommettes.length === 0) {
    tbody.querySelectorAll("tr").forEach((row) => {
      row.hidden = false;
    });
  } else {
    const tags = gommettes.join(" || ");
    const data = await fetchOpera(tags);
    const urns = data
      .map((d) => {
        const extra = d.data?.extra;
        if (!extra) return null;
        const line = extra.split("\n").find((l) => l.startsWith("CTS URN"));
        if (!line) return null;
        return line.replace("CTS URN:", "").trim();
      })
      .filter(Boolean);

    tbody.querySelectorAll("tr").forEach((row) => {
      const cts = row.dataset.cts;
      row.hidden = !urns.some((urn) => cts.startsWith(urn));
    });
  }

  // Second pass: hide duplicate works if ignorer-doublons is checked.
  // The work-level URN (everything before the final ".edition" component)
  // is used as the deduplication key; only the first row for each work is kept.
  const shouldDeduplicate =
    document.getElementById("ignorer-doublons")?.checked ?? false;
  if (shouldDeduplicate) {
    const seen = new Set();
    tbody.querySelectorAll("tr:not([hidden])").forEach((row) => {
      const workUrn = row.dataset.cts.replace(/\.[^.]+$/, "");
      if (seen.has(workUrn)) {
        row.hidden = true;
      } else {
        seen.add(workUrn);
      }
    });
  }
}