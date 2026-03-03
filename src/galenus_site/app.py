import json

from pathlib import Path

from flask import abort, redirect, render_template, url_for

from kodon_py.config import default_config
from kodon_py.server import create_app, load_passage_from_urn, load_toc_from_urn

from galenus_site.build import (
    _format_critical_edition,
    _format_modern_translation,
    _int_or_zero,
)
from galenus_site.reading import (
    get_iiif_config,
    load_editions,
    load_images_config,
    parse_nav_html,
)
from galenus_site.zotero import SORT_ORDERS, read_zotero_json

APP_DIR = Path(__file__).resolve().parent
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
JSON_DIR = (ROOT_DIR / "tei_json").absolute()


def _extract_cts_urn(extra: str) -> str | None:
    """Extract a CTS URN from a Zotero item's 'extra' field."""
    if not isinstance(extra, str):
        return None
    for line in extra.split("\n"):
        if line.startswith("CTS URN: "):
            return line.split("CTS URN: ", 1)[1].strip()
    return None


def main():
    """Run the development server."""
    config = default_config

    config["static_folder"] = (APP_DIR / "static").absolute()
    config["template_folder"] = (APP_DIR / "templates").absolute()

    app = create_app(
        json_dir=JSON_DIR,
        config=config,
    )

    @app.route("/")
    def index():
        zotero_data = read_zotero_json()

        for item in zotero_data:
            for edition in item.get("criticalEditions", []):
                edition["_formatted"] = _format_critical_edition(edition)
            for translation in item.get("modernTranslations", []):
                translation["_formatted"] = _format_modern_translation(translation)
            for edition in item.get("verbatimEditions", []):
                cts_urn = _extract_cts_urn(edition.get("extra", ""))
                edition["_route"] = url_for("reading", urn=cts_urn) if cts_urn else "#"

        items = sorted(
            [i for i in zotero_data if i.get("callNumber")],
            key=lambda i: _int_or_zero(i["callNumber"]),
        )

        sorted_lists: dict[str, list] = {}
        for key, info in SORT_ORDERS.items():
            sorted_lists[key] = info["sort_fn"](zotero_data)

        return render_template(
            "index.html.jinja",
            items=items,
            sorted_lists=sorted_lists,
            sort_orders=SORT_ORDERS,
            default_sort="kuehn",
        )

    @app.route("/recherche")
    def text_search():
        return render_template("text_search.html.jinja")

    @app.route("/titres")
    def titres():
        editions = load_editions()
        zotero_data = read_zotero_json()

        # Build lookup from work-level CTS URN to multi-language titles
        cts_to_titles: dict[str, dict] = {}
        for opus in zotero_data:
            cts_urn = opus.get("ctsURN")
            if cts_urn:
                cts_to_titles[cts_urn] = {
                    "greek_title": opus.get("greekTitle"),
                    "latin_title": opus.get("latinTitle"),
                    "french_title": opus.get("frenchTitle"),
                    "english_title": opus.get("englishTitle"),
                }

        # Enrich editions with multi-language titles
        for edition in editions:
            edition_cts = edition.get("cts", "")
            titles = next(
                (t for cts, t in cts_to_titles.items() if edition_cts.startswith(cts)),
                None,
            )
            if titles:
                edition.update(titles)
            else:
                edition.setdefault("greek_title", None)
                edition.setdefault("latin_title", edition.get("title"))
                edition.setdefault("french_title", None)
                edition.setdefault("english_title", None)

        all_tags = ["gen", "anat", "physiol", "nosol", "therap", "pharm", "Hipp", "phil"]

        return render_template("search.html.jinja", editions=editions, all_tags=all_tags)

    @app.route("/<path:urn>")
    def reading(urn):
        """Text reader page for a given CTS URN."""

        text_containers = load_passage_from_urn(urn, JSON_DIR)

        if text_containers is None:
            abort(404)

        images_data = load_images_config()
        toc = load_toc_from_urn(urn, JSON_DIR)
        zotero_data = read_zotero_json()

        zotero_item = None

        for item in zotero_data:
            item_urn = item.get("ctsURN", "")

            if item_urn is not None and urn.startswith(item_urn):
                zotero_item = item
                break

        if zotero_item is None:
            print(f"No zotero item found for {urn}")

        for edition in zotero_item.get("criticalEditions", []):
            edition["_formatted"] = _format_critical_edition(edition)
        for translation in zotero_item.get("modernTranslations", []):
            translation["_formatted"] = _format_modern_translation(translation)
        for edition in zotero_item.get("verbatimEditions", []):
            cts_urn = _extract_cts_urn(edition.get("extra", ""))
            edition["_route"] = url_for("reading", urn=cts_urn) if cts_urn else "#"

        volume = zotero_item.get("volume")
        imgkuhn = get_iiif_config(images_data, cts_urn, volume)
        image_vars = None

        if imgkuhn:
            image_vars = f"var imgkuhn = {json.dumps(imgkuhn)};"

        return render_template(
            "reading.html.jinja",
            edition_title=toc.get("title", ""),
            toc=toc,
            current_urn=urn,
            text_containers=text_containers,
            image_vars=image_vars,
            zotero_item=zotero_item,
        )

    app.run(debug=True)

    return app
