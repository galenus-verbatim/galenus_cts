import re

from collections import Counter, deque
from pathlib import Path
from sys import _current_frames
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

        self.lang = None
        self.urn = None

        self.current_lb_n = 1
        self.current_pb_n = None
        self.current_text = ""
        self.current_textpart_urn = None

        self.blocks = []
        self.element_stack = deque()
        self.textpart_labels = set()
        self.textpart_stack = deque()
        self.unhandled_elements = set()

        # this feels wrong coming from web-development world
        for body in tree.iterfind(".//tei:body", namespaces=NAMESPACES):
            lxml.sax.saxify(body, self)

    def create_table_of_contents(self):
        textparts = [
            dict(
                label=f"{t['subtype'].capitalize()} {t.get('n', '')}".strip(),
                urn=t["urn"],
                subtype=t["subtype"],
            )
            for t in self.blocks
            if t.get("type") == "textpart"
        ]

        if len(self.textpart_labels) == 1:
            return textparts

        hierarchy = list(self.textpart_labels)

        def nest_textparts(textparts):
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
                    item["children"] = list(reversed(children))

                stack.append((level, item))

            return [item for level, item in stack]

        return nest_textparts(textparts)

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
            self.textpart_stack.append(attrs)
            self.textpart_labels.add(attrs["subtype"])
            citation_fragment = attrs.get("id", attrs.get("n", "")).replace("_", "")

            if len(citation_fragment) == 0:
                print(f"Incorrectly labeled textpart: {attrs}")
            else:
                citation_fragment = f":{citation_fragment}"

            self.current_textpart_urn = f"{self.urn}{citation_fragment}"
            self.current_text = ""

    def handle_element(self, tagname: str, attrs: dict):
        attrs.update(
            {
                "tagname": tagname,
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
        else:
            self.current_lb_n = int(attrs.get("n", "1"))

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

        if localname == "div" and len(self.textpart_stack) > 0:
            # NOTE: page and line numbers don't reset when the textpart changes
            textpart = self.textpart_stack.pop()

            textpart.update(
                {
                    "content": self.current_text.strip(),
                    "line": self.current_lb_n,
                    "page": self.current_pb_n,
                    "tokens": re.split(r"\s+", self.current_text.strip()),
                    "urn": self.current_textpart_urn,
                }
            )
            self.blocks.append(textpart)
            return

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
                "head"
                | "l"
                | "label"
                | "lg"
                | "milestone"
                | "note"
                | "num"
                | "p"
                | "quote"
            ):
                return self.handle_element(localname, clean_attrs)
            case "lb":
                return self.handle_lb(clean_attrs)
            case "pb":
                return self.handle_pb(clean_attrs)
            case _:
                print(f"Unknown element {localname} in {self.current_textpart_urn}")
                self.unhandled_elements.add(localname)
                self.handle_element(localname, clean_attrs)


if __name__ == "__main__":
    handler = GVSaxParser("./data/tlg0057/tlg037/tlg0057.tlg037.1st1K-grc1.xml")

    print(handler.blocks[-1])
