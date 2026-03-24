from __future__ import annotations

import json
import re

from pathlib import Path

JSON_DIR = Path(__file__).resolve().parent / "static" / "json"


def parse_nav_html(nav_html: str) -> list[dict[str, str]]:
    """Extract chapter URNs and labels from editions.json nav HTML.

    Returns a list of {"urn": "...", "label": "..."} dicts.
    """
    if not nav_html:
        return []
    chapters: list[dict[str, str]] = []
    for match in re.finditer(r'href="\./([^"]+)"[^>]*>([^<]+)<', nav_html):
        chapters.append({"urn": match.group(1), "label": match.group(2).strip()})
    return chapters


def load_editions(editions_path: str | Path | None = None) -> list[dict]:
    """Load editions.json, returning the list of edition dicts."""
    if editions_path is None:
        editions_path = JSON_DIR / "editions.json"
    return json.loads(Path(editions_path).read_text(encoding="utf-8"))


# Sample URL: https://numerabilis.u-paris.fr/iiif/2/bibnum:00013x02:0201/full/800,/0/default.jpg


def make_image_urls(bibnum: str, vol_pg: str):
    return f"https://numerabilis.u-paris.fr/iiif/2/bibnum:{bibnum}:{vol_pg}/full/800,/0/default.jpg"


def load_images_config(images_path: str | Path | None = None) -> dict:
    """Load galenus_images.json with IIIF volume configs.

    The JSON is keyed by edition name ("kuhn", "bale", "chartier", …), then by
    volume number string.  See static/json/README.md for the full schema.
    """
    if images_path is None:
        images_path = JSON_DIR / "galenus_images.json"
    return json.loads(Path(images_path).read_text(encoding="utf-8"))


def get_iiif_config(
    images_data: dict,
    cts_urn: str,
    volume: str | None,
    edition: str = "kuhn",
    abbr: str = "K",
) -> dict[str, Any] | None:
    """Build a JS image-config dict for a given edition and volume.

    Looks up ``volume`` in ``images_data[edition]`` and returns a dict that
    app.py serialises to a JS variable (e.g. ``var imgkuhn = {...};``) in the
    reading template.  galenus.js uses that object to attach click handlers to
    edition page-break spans, computing the physical IIIF image index as
    ``pad(edition_page + pdiff, 4)`` and substituting it for ``%%`` in the URL
    template.

    Parameters
    ----------
    images_data:
        The full dict loaded from galenus_images.json.
    cts_urn:
        The CTS URN of the passage being displayed (currently unused; reserved
        for future per-work overrides).
    volume:
        The edition volume number string from Zotero (e.g. ``"2"`` or
        ``"1-2"``).  When a range like ``"1-2"`` is given, the first volume is
        used.
    edition:
        Top-level key in galenus_images.json identifying the edition
        (``"kuhn"``, ``"bale"``, ``"chartier"``).  Defaults to ``"kuhn"``.
    abbr:
        Short citation abbreviation shown in the UI (e.g. ``"K"`` for Kühn,
        ``"B"`` for Bâle, ``"Ch"`` for Chartier).  Defaults to ``"K"``.

    Returns
    -------
    dict | None
        A JS-ready config dict with the keys below, or ``None`` if no matching
        volume config exists.

        ``pdiff``
            Integer offset added to the printed edition page number to obtain
            the physical image index in the IIIF sequence.
        ``vol``
            The resolved volume number string (first element when a range was
            given).
        ``abbr``
            Short citation abbreviation shown in the UI.
        ``url``
            IIIF image URL template.  ``%%`` is replaced at runtime with the
            zero-padded 4-digit physical page index.
        ``title``
            HTML anchor string used as the image caption / source link.  ``%%``
            is likewise replaced at runtime.
    """
    if not volume:
        return None

    # Volume may be "1-2" — use the first volume
    vol = volume.split("-")[0].strip()

    vol_config = images_data.get(edition, {}).get(vol)
    if not vol_config:
        return None

    return {
        "pdiff": vol_config.get("pdiff", 0),
        "vol": vol,
        "abbr": abbr,
        "url": vol_config.get("url", ""),
        "title": vol_config.get("title", ""),
    }
