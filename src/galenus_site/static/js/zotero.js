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
