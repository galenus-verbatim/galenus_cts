from pathlib import Path

from feedparser import namespaces
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
            p = chapter.find("./tei:p", namespaces=NAMESPACES)

            assert (
                p is not None
            ), f"p element not defined for chapter {chapter} in {self.urn}"

            children = self.get_children(p)

            c = {"n": chapter.get("n"), "children": children}
            chapters.append(c)

        return chapters

    def get_children(self, p):
        return [self._handle_child(child) for child in p.iterchildren()]

    def _handle_child(self, child):
        if child.get("n") is not None:
            return {
                "attributes": dict(child.attrib),
                "subtype": child.tag,
                "content": child.tail,
                "type": "text_element",
            }

        else:
            return {
                "attributes": dict(child.attrib),
                "subtype": child.tag,
                "content": etree.tostring(child, encoding="unicode", with_tail=True),
                "type": "text_element",
            }


## Current index page navigation built via
## information from Zotero:
## {volume number}.{page numbers} -- is this a bug in the XSL that it only shows the first page?
## fichtner no. (stored as "call no." ?)
## title
## cts urn --> #-link to scroll to page
## other URL
