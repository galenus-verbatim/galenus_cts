## TODO
# - [ ] Add license and funding statement

from collections import deque
from pathlib import Path
from xml.sax import xmlreader
from xml.sax.handler import ContentHandler

import lxml.sax  # pyright: ignore

from lxml import etree


NAMESPACES = {"tei": "http://www.tei-c.org/ns/1.0"}


def remove_ns_from_attrs(attrs: xmlreader.AttributesNSImpl):
    a = {}

    for k, v in attrs.items():
        ns, localname = k

        a[localname] = v

    return a


def nest_textparts(textparts, hierarchy):
    stack = []

    for item in textparts:
        level = hierarchy.index(item["subtype"])

        if len(stack) == 0:
            stack.append((level, item))
            continue

        children = []

        while stack and stack[-1][0] > level:
            children.append(stack.pop()[1])

        if children:
            item["subpassages"] = list(reversed(children))

        stack.append((level, item))

    return [item for level, item in stack]


class GVSaxParser(ContentHandler):
    def __init__(self, filename: Path | str):
        tree = etree.parse(filename)

        self.lang = None
        self.urn = None

        self.current_text = ""
        self.current_textpart_location = None
        self.current_textpart_urn = None

        self.element_stack = deque()
        self.elements = []
        self.textpart_labels = []
        self.textpart_stack = deque()
        self.textparts = []
        self.unhandled_elements = set()

        for body in tree.iterfind(".//tei:body", namespaces=NAMESPACES):
            lxml.sax.saxify(body, self)

    def create_table_of_contents(self):
        textparts = [
            dict(
                label=f"{t['subtype'].capitalize()} {t.get('n', '')}".strip(),
                urn=t["urn"],
                subtype=t["subtype"],
            )
            for t in self.textparts
            if t.get("type") == "textpart"
        ]

        if len(self.textpart_labels) == 1:
            return textparts

        hierarchy = list(self.textpart_labels)

        return nest_textparts(textparts, hierarchy)

    def handle_div(self, attrs: dict):
        if attrs["type"] == "edition":
            self.lang = attrs["lang"]
            self.urn = attrs["n"]

        elif attrs["type"] == "textpart":
            subtype = attrs.get("subtype")

            if subtype is not None and subtype not in self.textpart_labels:
                self.textpart_labels.append(attrs["subtype"])

            citation_n = attrs.get("n")

            if citation_n is None:
                print(f"Unnumbered textpart: {attrs}")

            location = []

            for n in [t.get("n") for t in self.textpart_stack]:
                if n is not None:
                    location.append(n)

            if citation_n is not None:
                location.append(citation_n)

            self.current_textpart_location = location
            self.current_textpart_urn = f"{self.urn}:{'.'.join(self.current_textpart_location)}"
            self.current_text = ""

            attrs.update(
                {
                    "index": len(self.textparts),
                    "location": location,
                    "offset": 0,
                    "urn": self.current_textpart_urn,
                }
            )

            self.textpart_stack.append(attrs)

    def handle_element(self, tagname: str, attrs: dict):
        self.current_text += " "

        attrs.update(
            {
                "index": len(self.elements),
                "tagname": tagname,
                "offset": len(self.current_text),
                "textpart_index": len(self.textparts),
                "urn": self.current_textpart_urn,
            }
        )

        self.element_stack.append(attrs)

    def characters(self, content: str) -> None:
        self.current_text += content

    def endElementNS(self, name: tuple[str | None, str], qname: str | None) -> None:
        uri, localname = name

        if localname == "div" and len(self.textpart_stack) > 0:
            textpart = self.textpart_stack.pop()

            textpart.update(
                {
                    "end_offset": len(self.current_text),
                    "text": self.current_text,
                }
            )
            self.textparts.append(textpart)
            self.current_text = ""

        elif len(self.element_stack) > 0:
            el = self.element_stack.pop()

            el.update(
                {
                    "end_offset": len(self.current_text),
                    "urn": el.get("urn", self.current_textpart_urn),
                }
            )
            self.elements.append(el)

    def startElementNS(
        self,
        name: tuple[str | None, str],
        qname: str | None,
        attrs: xmlreader.AttributesNSImpl,
    ) -> None:
        uri, localname = name
        clean_attrs = remove_ns_from_attrs(attrs)

        match localname:
            case "body":
                pass
            case "div":
                return self.handle_div(clean_attrs)
            # the reason we're being explicit about the elements we handle with `handle_element()`,
            # even though this is also the default function (below), is because we want to make
            # sure that we keep a running set of elements that we know behave properly when
            # handled this way. By keeping track of elements that we _don't_ handle, we can
            # incrementally add handlers for edge-cases as needed.
            case (
                "choice"
                | "corr"
                | "del"
                | "foreign"
                | "gap"
                | "head"
                | "hi"
                | "l"
                | "label"
                | "lb"
                | "lg"
                | "milestone"
                | "note"
                | "num"
                | "p"
                | "pb"
                | "quote"
                | "sic"
            ):
                return self.handle_element(localname, clean_attrs)
            case _:
                print(f"Unknown element {localname} in {self.current_textpart_urn}")
                self.unhandled_elements.add(localname)
                self.handle_element(localname, clean_attrs)


if __name__ == "__main__":
    handler = GVSaxParser("./data/tlg0530/tlg029/tlg0530.tlg029.verbatim-lat1.xml")

    for t in handler.textparts:
        print(
            f"{t['type']}\t{t['subtype']}\t{t.get('n', '')}\t{t['offset']}\t{t['end_offset']}\t{t['urn']}"
        )
