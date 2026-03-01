"""Port of gv-static/src/lib/zotero.ts — reads and processes Zotero JSON data."""

from __future__ import annotations

import json
import locale
from pathlib import Path
from typing import Any

COLLECTION_IDS_TO_NAMES: dict[str, str] = {
    "9QP457XQ": "Editiones criticae",
    "XWUKKHRC": "Editiones verbatim",
    "ZTP7ASC3": "Editiones veterae",
    "EEF8L3QT": "Galeni et Pseudo-Galeni opera",
    "DTQ8XZKP": "Libri ad Galenum pertinentes",
    "2XYEX7QT": "Translationes recentiores",
    "J4EMVD4V": "Translationes verbatim",
}

COLLECTION_NAMES_TO_IDS: dict[str, str] = {
    v: k for k, v in COLLECTION_IDS_TO_NAMES.items()
}

# Path to Zotero JSON data relative to this file
ZOTERO_JSON_PATH = (
    Path(__file__).resolve().parent / "static" / "json" / "gv_zotero.json"
)


def _load_raw_items(path: Path | None = None) -> list[dict[str, Any]]:
    p = path or ZOTERO_JSON_PATH
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def _get_collection_by_name(
    raw_items: list[dict[str, Any]], collection_name: str
) -> list[dict[str, Any]]:
    coll_id = COLLECTION_NAMES_TO_IDS[collection_name]
    return [
        item["data"]
        for item in raw_items
        if coll_id in (item.get("data", {}).get("collections") or [])
    ]


def _parse_extra(extra: str | None) -> dict[str, str]:
    if not extra:
        return {}
    result: dict[str, str] = {}
    for line in extra.split("\n"):
        parts = line.split(": ", 1)
        if len(parts) == 2:
            result[parts[0].strip()] = parts[1].strip()
    return result


def _find_creator(creators: list[dict], creator_type: str) -> dict | None:
    for c in creators:
        if c.get("creatorType") == creator_type:
            return c
    return None


def _find_creator_with_lastname(creators: list[dict]) -> dict | None:
    for c in creators:
        if c.get("lastName"):
            return c
    return None


def read_zotero_json(path: Path | None = None) -> list[dict[str, Any]]:
    """Read and process the Zotero JSON export, returning enriched opera items."""
    raw_items = _load_raw_items(path)

    editiones_criticae = _get_collection_by_name(raw_items, "Editiones criticae")
    editiones_verbatim = _get_collection_by_name(raw_items, "Editiones verbatim")
    editiones_veterae = _get_collection_by_name(raw_items, "Editiones veterae")
    opera = _get_collection_by_name(raw_items, "Galeni et Pseudo-Galeni opera")
    translationes_recentiores = _get_collection_by_name(
        raw_items, "Translationes recentiores"
    )
    translationes_verbatim = _get_collection_by_name(
        raw_items, "Translationes verbatim"
    )

    all_attachments = [
        item["data"]
        for item in raw_items
        if item.get("data", {}).get("itemType") == "attachment"
    ]
    all_notes = [
        item["data"]
        for item in raw_items
        if item.get("data", {}).get("itemType") == "note"
    ]

    results = []

    for opus in opera:
        attachments = [a for a in all_attachments if a.get("parentItem") == opus["key"]]
        fichtner_number = opus.get("callNumber")

        fichtner_url = None
        gal_lat_url = None
        for a in attachments:
            if a.get("title") == "Fichtner Bibliographie":
                fichtner_url = a.get("url")
            if a.get("title") == "Galeno Latino":
                gal_lat_url = a.get("url")

        ancient_edition = next(
            (
                item
                for item in editiones_veterae
                if item.get("callNumber") == fichtner_number
            ),
            None,
        )
        author = _find_creator(opus.get("creators", []), "author")
        critical_editions = [
            item
            for item in editiones_criticae
            if item.get("callNumber") == fichtner_number
        ]
        kuehn_edition = next(
            (
                item
                for item in translationes_verbatim
                if item.get("callNumber") == fichtner_number
                and any(c.get("lastName") == "Kühn" for c in item.get("creators", []))
            ),
            None,
        )
        modern_translations = [
            item
            for item in translationes_recentiores
            if item.get("callNumber") == fichtner_number
        ]
        notes = [n for n in all_notes if n.get("parentItem") == opus["key"]]
        verbatim_editions = [
            item
            for item in editiones_verbatim
            if item.get("callNumber") == fichtner_number
        ]

        extra = _parse_extra(opus.get("extra"))

        result: dict[str, Any] = {
            **opus,
            "ancientEdition": ancient_edition,
            "attachments": attachments,
            "author": author,
            "criticalEditions": critical_editions,
            "ctsURN": extra.get("CTS URN"),
            "englishTitle": extra.get("English Title"),
            "englishShortTitle": extra.get("English Short Title"),
            "extra": extra,
            "fichtnerNumber": fichtner_number,
            "fichtnerURL": fichtner_url,
            "frenchTitle": extra.get("French Title"),
            "galLatURL": gal_lat_url,
            "greekTitle": extra.get("Original Title"),
            "kuehnEdition": kuehn_edition,
            "kuehnEditionKey": kuehn_edition["key"] if kuehn_edition else None,
            "kuehnEditionTitle": kuehn_edition["title"] if kuehn_edition else None,
            "kuehnEditionPages": kuehn_edition.get("pages") if kuehn_edition else None,
            "kuehnEditionVolume": (
                kuehn_edition.get("volume") if kuehn_edition else None
            ),
            "latinAbbreviatedTitle": opus.get("shortTitle"),
            "latinTitle": kuehn_edition["title"] if kuehn_edition else None,
            "modernTranslations": modern_translations,
            "notes": notes,
            "tags": [tag["tag"] for tag in opus.get("tags", [])],
            "verbatimEditions": verbatim_editions,
        }
        results.append(result)

    return results


# ---------------------------------------------------------------------------
# Sorting helpers — one per <select> option in the landing page
# ---------------------------------------------------------------------------


def _int_or_zero(s: str | None) -> int:
    if not s:
        return 0
    try:
        return int(s)
    except ValueError:
        return 0


def sort_by_latin_title(items: list[dict]) -> list[dict]:
    """titLat — localeCompare on latinTitle (fallback to title)."""
    return sorted(
        items, key=lambda i: (i.get("latinTitle") or i.get("title") or "").lower()
    )


def sort_by_fichtner(items: list[dict]) -> list[dict]:
    """fichtner — numeric sort on callNumber."""
    with_cn = [i for i in items if i.get("callNumber")]
    return sorted(with_cn, key=lambda i: _int_or_zero(i["callNumber"]))


def sort_by_kuehn(items: list[dict]) -> list[dict]:
    """kuehn — by volume then first page."""
    with_kuehn = [i for i in items if i.get("kuehnEditionVolume")]
    return sorted(
        with_kuehn,
        key=lambda i: (
            _int_or_zero(i.get("kuehnEditionVolume")),
            _int_or_zero((i.get("kuehnEditionPages") or "").split("-")[0]),
        ),
    )


def sort_by_cmg_abbreviation(items: list[dict]) -> list[dict]:
    """titLatAbbr — localeCompare on latinAbbreviatedTitle."""
    with_abbr = [i for i in items if i.get("latinAbbreviatedTitle")]
    return sorted(with_abbr, key=lambda i: (i["latinAbbreviatedTitle"] or "").lower())


def sort_by_greek_title(items: list[dict]) -> list[dict]:
    """titGrc — localeCompare on greekTitle."""
    with_grc = [i for i in items if i.get("callNumber") and i.get("greekTitle")]
    return sorted(with_grc, key=lambda i: i["greekTitle"] or "")


def sort_by_french_title(items: list[dict]) -> list[dict]:
    """titFra — localeCompare on frenchTitle, only items with frenchTitle."""
    with_fr = [i for i in items if i.get("callNumber") and i.get("frenchTitle")]
    return sorted(with_fr, key=lambda i: (i["frenchTitle"] or "").lower())


def sort_by_english_title(items: list[dict]) -> list[dict]:
    """titEng — localeCompare on englishTitle."""
    with_en = [i for i in items if i.get("callNumber") and i.get("englishTitle")]
    return sorted(with_en, key=lambda i: (i["englishTitle"] or "").lower())


def sort_by_cgt_abbreviation(items: list[dict]) -> list[dict]:
    """titEngAbbr — localeCompare on englishShortTitle."""
    with_abbr = [i for i in items if i.get("callNumber") and i.get("englishShortTitle")]
    return sorted(with_abbr, key=lambda i: (i["englishShortTitle"] or "").lower())


# Ordered dict of sort keys matching the <select> options
SORT_ORDERS: dict[str, dict[str, Any]] = {
    "titLat": {"label": "Titre latin", "sort_fn": sort_by_latin_title},
    "fichtner": {"label": "\u2116 Fichtner", "sort_fn": sort_by_fichtner},
    "kuehn": {"label": "Édition Kühn", "sort_fn": sort_by_kuehn},
    "titLatAbbr": {
        "label": "Abréviation CMG",
        "sort_fn": sort_by_cmg_abbreviation,
    },
    "titGrc": {"label": "Titre grec", "sort_fn": sort_by_greek_title},
    "titFra": {"label": "Titre français", "sort_fn": sort_by_french_title},
    "titEng": {"label": "Titre anglais", "sort_fn": sort_by_english_title},
    "titEngAbbr": {
        "label": "Abréviation CGT",
        "sort_fn": sort_by_cgt_abbreviation,
    },
}
