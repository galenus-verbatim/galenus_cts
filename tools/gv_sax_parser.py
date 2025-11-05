import re

from collections import Counter, deque
from pathlib import Path
from xml.sax import xmlreader
from xml.sax.handler import ContentHandler

import lxml.sax  # pyright: ignore

from lxml import etree


NAMESPACES = {"tei": "http://www.tei-c.org/ns/1.0"}
SELF_CLOSING_ELEMENTS = ("lb", "milestone", "pb")


def remove_ns_from_attrs(attrs: xmlreader.AttributesNSImpl):
    a = {}

    for k, v in attrs.items():
        ns, localname = k

        a[localname] = v

    return a


class GVSaxParser(ContentHandler):
    def __init__(self, filename: Path | str):
        tree = etree.parse(filename)
        body = tree.find(".//tei:body", namespaces=NAMESPACES)

        self.lang = None
        self.urn = None

        self.current_lb_n = 1
        self.current_pb_n = None
        self.current_textpart_urn = None
        self.current_text = ""

        self.blocks = []
        self.element_stack = deque()
        self.textpart_labels = set()

        lxml.sax.saxify(body, self)

    def get_current_token_offset(self):
        if len(self.current_text) > 0:
            split = re.split(r"\s+", self.current_text.strip())
            current_token = split[-1]
            counts = Counter(split)
            current_token_index = counts[current_token]

            return f"{current_token}[{current_token_index}]"

    def handle_div(self, attrs):
        if attrs["type"] == "edition":
            self.lang = attrs["lang"]
            self.urn = attrs["n"]
        elif attrs["type"] == "textpart":
            self.textpart_labels.add(attrs["subtype"])
            citation_fragment = attrs.get("id", attrs.get("n", "")).replace("_", "")

            if len(citation_fragment) == 0:
                print(f"Incorrectly labeled textpart: {attrs}")
            else:
                citation_fragment = f":{citation_fragment}"

            self.current_textpart_urn = f"{self.urn}{citation_fragment}"
            self.current_text = ""

    def handle_head(self, attrs):
        attrs.update(
            {
                "tagname": "head",
                "char_offset": len(self.current_text),
                "line": self.current_lb_n,
                "page": self.current_pb_n,
                "token_offset": self.get_current_token_offset(),
                "urn": self.current_textpart_urn,
            }
        )

        self.element_stack.append(attrs)

    def handle_label(self, attrs: dict):
        attrs.update(
            {
                "tagname": "label",
                "char_offset": len(self.current_text),
                "line": self.current_lb_n,
                "page": self.current_pb_n,
                "token_offset": self.get_current_token_offset(),
                "urn": self.current_textpart_urn,
            }
        )

        self.element_stack.append(attrs)

    def handle_lb(self, attrs: dict):
        if attrs.get("n") is None:
            attrs.update({"n": self.current_lb_n})
            self.current_lb_n += 1

        attrs.update(
            {
                "tagname": "lb",
                "char_offset": len(self.current_text),
                "page": self.current_pb_n,
                "token_offset": self.get_current_token_offset(),
                "urn": self.current_textpart_urn,
            }
        )

        self.blocks.append(attrs)

    def handle_milestone(self, attrs: dict):
        attrs.update(
            {
                "tagname": "milestone",
                "char_offset": len(self.current_text),
                "line": self.current_lb_n,
                "page": self.current_pb_n,
                "token_offset": self.get_current_token_offset(),
                "urn": self.current_textpart_urn,
            }
        )

        self.blocks.append(attrs)

    def handle_num(self, attrs: dict):
        attrs.update(
            {
                "tagname": "num",
                "char_offset": len(self.current_text),
                "line": self.current_lb_n,
                "page": self.current_pb_n,
                "token_offset": self.get_current_token_offset(),
                "urn": self.current_textpart_urn,
            }
        )

        self.element_stack.append(attrs)

    def handle_p(self, attrs: dict):
        attrs.update(
            {
                "tagname": "p",
                "char_offset": len(self.current_text),
                "line": self.current_lb_n,
                "page": self.current_pb_n,
                "token_offset": self.get_current_token_offset(),
                "urn": self.current_textpart_urn,
            }
        )

        self.element_stack.append(attrs)

    def handle_pb(self, attrs: dict):
        attrs.update(
            {
                "tagname": "pb",
                "char_offset": len(self.current_text),
                "token_offset": self.get_current_token_offset(),
                "urn": self.current_textpart_urn,
            }
        )
        self.current_lb_n = 1
        self.current_pb_n = attrs["n"]

        self.blocks.append(attrs)

    def characters(self, content: str) -> None:
        if len(content.strip()) == 0:
            return

        self.current_text += f" {content.strip()}"

    def endElementNS(self, name: tuple[str, str], qname: str) -> None:
        uri, localname = name

        if localname == "div":
            # NOTE: page and line numbers don't reset when the textpart changes

            self.blocks.append(
                {
                    "type": "text",
                    "content": self.current_text.strip(),
                    "line": self.current_lb_n,
                    "page": self.current_pb_n,
                    "tokens": re.split(r"\s+", self.current_text.strip()),
                    "urn": self.current_textpart_urn,
                }
            )

        if localname in SELF_CLOSING_ELEMENTS:
            pass

        if len(self.element_stack) > 0:
            el = self.element_stack.pop()

            el.update(
                {
                    "end_char_offset": len(self.current_text),
                    "end_token_offset": self.get_current_token_offset(),
                }
            )

            self.blocks.append(el)

    def startElementNS(
        self, name: tuple[str, str], qname: str, attrs: xmlreader.AttributesNSImpl
    ) -> None:
        uri, localname = name
        clean_attrs = remove_ns_from_attrs(attrs)

        match localname:
            case "div":
                self.handle_div(clean_attrs)
            case "head":
                self.handle_head(clean_attrs)
            case "label":
                self.handle_label(clean_attrs)
            case "lb":
                self.handle_lb(clean_attrs)
            case "milestone":
                self.handle_milestone(clean_attrs)
            case "num":
                self.handle_num(clean_attrs)
            case "p":
                self.handle_p(clean_attrs)
            case "pb":
                self.handle_pb(clean_attrs)


if __name__ == "__main__":
    handler = GVSaxParser("./data/tlg0057/tlg037/tlg0057.tlg037.1st1K-grc1.xml")

    print(handler.blocks[-1])
