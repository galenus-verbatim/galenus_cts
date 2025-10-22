from pathlib import Path

from lxml import etree
from pyzotero import zotero

NAMESPACES = {
    "tei": "http://www.tei-c.org/ns/1.0",
}

ZOTERO_LIBRARY_ID = "4571007"
ZOTERO_LIBRARY_TYPE = "group"

zot = zotero.Zotero(ZOTERO_LIBRARY_ID, ZOTERO_LIBRARY_TYPE)


def get_zotero_items():
    return zot.everything(zot.items())


class GVDocument:
    def __init__(self, filename: Path):
        self.filename = str(filename)
        self.tree = etree.parse(filename)
        self.urn = f"urn:cts:greekLit:{filename.name.replace('.xml', '')}"
        self.chapters = self.get_chapters()

    def get_chapters(self):
        chapters = []

        for chapter in self.tree.iterfind(
            ".//tei:div[@subtype='chapter']", namespaces=NAMESPACES
        ):
            c = {"n": chapter.get("n")}
            p = chapter.find("./tei:p", namespaces=NAMESPACES)

            if p is not None:
                c["content"] = etree.tostring(p, encoding="unicode")

            chapters.append(c)

        return chapters


## Current index page navigation built via
## information from Zotero:
## {volume number}.{page numbers} -- is this a bug in the XSL that it only shows the first page?
## fichtner no. (stored as "call no." ?)
## title
## cts urn --> #-link to scroll to page
## other URL
