## TODO
# - [ ] Add license and funding statement

import logging

import re
import string

from pathlib import Path
from xml.sax import xmlreader
from xml.sax.handler import ContentHandler

import lxml.sax  # pyright: ignore

from lxml import etree


NAMESPACES = {"tei": "http://www.tei-c.org/ns/1.0"}

PUNCTUATION_TABLE = str.maketrans("", "", string.punctuation + "·")

# create logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

file_handler = logging.FileHandler(f"./tmp/{__name__}.log", mode="w")

formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

console_handler.setFormatter(formatter)
file_handler.setFormatter(formatter)

logger.addHandler(console_handler)
logger.addHandler(file_handler)


def get_first_token(s: str):
    tokens = [t for t in tokenize(s) if t.strip() != ""]

    if len(tokens) > 0:
        return tokens[0]

    return None


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


def tokenize(s: str):
    return re.split(r"\s+", s.strip().translate(PUNCTUATION_TABLE))


class GVSaxParser(ContentHandler):
    def __init__(self, filename: Path | str):
        self.logger = logger

        tree = etree.parse(filename)

        self.lang = None
        self.urn = None

        self.current_text = ""
        self.current_textpart_location = None
        self.current_textpart_urn = None

        self.element_stack = []
        self.elements = []
        self.textpart_labels = []
        self.textpart_stack = []
        self.textparts = []
        self.unhandled_elements = set()

        for body in tree.iterfind(".//tei:body", namespaces=NAMESPACES):
            lxml.sax.saxify(body, self)

    def add_textpart_to_stack(self, attrs: dict):
        subtype = attrs.get("subtype")

        if subtype is not None and subtype not in self.textpart_labels:
            self.textpart_labels.append(subtype)

        location = self.determine_location(attrs)

        self.current_textpart_location = location
        self.current_textpart_urn = (
            f"{self.urn}:{'.'.join(self.current_textpart_location)}"
        )
        self.current_text = ""

        attrs.update(
            {
                "index": len(self.textpart_stack) + len(self.textparts),
                "location": location,
                "offset": 0,
                "urn": self.current_textpart_urn,
            }
        )

        self.textpart_stack.append(attrs)

    def add_text_to_element(self, content: str):
        most_recent_el = self.element_stack[-1]

        if most_recent_el.get("text") is None:
            most_recent_el["text"] = content
        else:
            most_recent_el["text"] += content

        token = get_first_token(most_recent_el["text"])

        if (
            token is not None
            and most_recent_el.get("first_token") is None
            and most_recent_el["text"].strip() != ""
        ):
            count = tokenize(self.current_text).count(token) + 1
            most_recent_el["first_token"] = f"{token}[{count}]"

    def add_text_to_textpart(self, content: str):
        most_recent_textpart = self.textpart_stack[-1]

        if most_recent_textpart.get("text") is None:
            most_recent_textpart["text"] = content
        else:
            most_recent_textpart["text"] += content

    def characters(self, content: str) -> None:
        if len(self.element_stack) > 0:
            self.add_text_to_element(content)

        if len(self.textpart_stack) > 0:
            self.add_text_to_textpart(content)

        self.current_text += content

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

    def determine_location(self, attrs: dict):
        citation_n = attrs.get("n")

        if citation_n is None:
            self.logger.debug(f"Unnumbered textpart: {attrs}")

        location = []

        for n in [t.get("n") for t in self.textpart_stack]:
            if n is not None:
                location.append(n)

        if citation_n is not None:
            location.append(citation_n)

        return location

    def endElementNS(self, name: tuple[str | None, str], qname: str | None) -> None:
        uri, localname = name

        if localname == "div" and len(self.textpart_stack) > 0:
            textpart = self.textpart_stack.pop()

            textpart.update(
                {
                    "end_offset": len(self.current_text),
                }
            )
            self.textparts.append(textpart)
            # Reset self.current_text after appending
            # to self.textparts to prevent leftover
            # text from being assigned to textparts
            # higher up in the hierarchy. For example,
            # if we have a book, chapter, section hierarchy,
            # the first book will not be closed until after
            # the last chapter and section. If we don't clear
            # the text after closing the final section in the book,
            # the section's text can be added erroneously to
            # the chapter _and_ the book once we reach their
            # respective close tags.

            if len(self.textpart_stack) > 0:
                self.current_text = self.textpart_stack[-1].get("text", "")

        elif len(self.element_stack) > 0:
            el = self.element_stack.pop()

            el.update(
                {
                    "end_offset": len(self.current_text),
                    "urn": el.get("urn", self.current_textpart_urn),
                }
            )
            self.elements.append(el)

    def handle_div(self, attrs: dict):
        if attrs["type"] == "edition":
            self.lang = attrs["lang"]
            self.urn = attrs["n"]

        elif attrs["type"] == "textpart":
            self.add_textpart_to_stack(attrs)

    def handle_element(self, tagname: str, attrs: dict):
        textpart_index = 0

        if len(self.textpart_stack) == 0:
            logger.warn(f"Elements should not appear outside of textparts. Check {tagname}, {attrs}")

            if len(self.textparts) > 0:
                textpart_index = self.textparts[-1]["index"] + 1
        else:
            textpart_index = self.textpart_stack[-1]["index"]

        attrs.update(
            {
                "index": len(self.element_stack) + len(self.elements),
                "tagname": tagname,
                "offset": len(self.current_text),
                "textpart_index": textpart_index,
                "urn": self.current_textpart_urn,
            }
        )

        # Add a space to the current text
        # so that adjacent elements don't
        # share an offset.
        self.current_text += " "

        self.element_stack.append(attrs)

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
            # By keeping track of elements that we _don't_ handle, we can
            # incrementally identify edge-cases and add handlers for them
            # as needed.
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
                self.logger.debug(
                    f"Unknown element {localname} in {self.current_textpart_urn}"
                )
                self.unhandled_elements.add(localname)
                self.handle_element(localname, clean_attrs)


if __name__ == "__main__":
    handler = GVSaxParser("./data/tlg0530/tlg029/tlg0530.tlg029.verbatim-lat1.xml")
    print("type\tsubtype\tn\t\toffset\tend_offset\turn")
    for t in handler.textparts:
        print(
            f"{t['type']}\t{t['subtype']}\t{t.get('n', 'n/a')[0:6]}\t{t['offset']}\t{t['end_offset']}\t{t['urn']}"
        )
