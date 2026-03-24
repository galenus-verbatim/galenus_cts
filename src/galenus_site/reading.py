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
    """Load galenus_images.json with IIIF volume configs."""
    if images_path is None:
        images_path = JSON_DIR / "galenus_images.json"
    return json.loads(Path(images_path).read_text(encoding="utf-8"))


def get_iiif_config(
    images_data: dict,
    cts_urn: str,
    volume: str | None,
) -> dict[str, Any] | None:
    """Build the imgkuhn JS config for a given edition.

    Uses the volume number from editions.json to look up
    Kühn IIIF config in galenus_images.json.
    """
    if not volume:
        return None

    # Volume may be "1-2" — use the first volume
    vol = volume.split("-")[0].strip()

    kuhn = images_data.get("kuhn", {})
    vol_config = kuhn.get(vol)
    if not vol_config:
        return None

    return {
        "pdiff": vol_config.get("pdiff", 0),
        "vol": vol,
        "abbr": "K",
        "url": vol_config.get("url", ""),
        "title": vol_config.get("title", ""),
    }
