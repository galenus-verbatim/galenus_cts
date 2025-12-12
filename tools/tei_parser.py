## TODO
# - [ ] Add license and funding statement
# - [ ] Explore lemmatization options: https://github.com/bowphs/SIGTYP-2024-hierarchical-transformers/issues/1

import logging
from pathlib import Path
from xml.sax import xmlreader
from xml.sax.handler import ContentHandler

import lxml.sax  # pyright: ignore
import stanza

from lxml import etree

DISABLED_PIPES = ["parser", "ner", "textcat"]

greek_tokenizer = stanza.Pipeline(
    "grc",
    processors="tokenize",
    package="perseus",
    model_dir="./stanza_models",
    download_method=stanza.DownloadMethod.REUSE_RESOURCES,
)
latin_tokenizer = stanza.Pipeline(
    "la",
    processors="tokenize",
    package="perseus",
    model_dir="./stanza_models",
    download_method=stanza.DownloadMethod.REUSE_RESOURCES,
)


NAMESPACES = {"tei": "http://www.tei-c.org/ns/1.0"}

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


def create_table_of_contents(textparts, textpart_labels):
    textparts = [
        dict(
            label=f"{t['subtype'].capitalize()} {t.get('n', '')}".strip(),
            urn=t["urn"],
            subtype=t["subtype"],
        )
        for t in textparts
        if t.get("type") == "textpart"
    ]

    if len(textpart_labels) == 1:
        return textparts

    hierarchy = list(textpart_labels)

    return nest_textparts(textparts, hierarchy)


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


def remove_ns_from_attrs(attrs: xmlreader.AttributesNSImpl):
    a = {}

    for k, v in attrs.items():
        ns, localname = k

        a[localname] = v

    return a


class TEIParser(ContentHandler):
    def __init__(self, filename: Path | str):
        tree = etree.parse(filename)

        self.lang = None
        self.urn = None

        self.current_tokens: list[str] = []
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

        attrs.update(
            {
                "index": len(self.textpart_stack) + len(self.textparts),
                "location": location,
                "urn": self.current_textpart_urn,
            }
        )

        self.textpart_stack.append(attrs)

    def characters(self, content: str) -> None:
        if len(self.element_stack) == 0:
            if content.strip() != "":
                logger.warning(
                    f"{self.urn}\nCharacters must belong to an element, but no elements are available."
                )
                logger.warning(content)
            return

        parent_element = self.element_stack[-1]
        tokens = self.tokenize(content)
        text_run = self.process_tokens(tokens)

        if len(text_run) > 0:
            parent_element["children"].append(text_run)

    def determine_location(self, attrs: dict):
        citation_n = attrs.get("n")

        if citation_n is None:
            logger.debug(f"{self.urn}\nUnnumbered textpart: {attrs}")

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

            self.textparts.append(textpart)

        elif len(self.element_stack) > 0:
            el = self.element_stack.pop()

            el.update(
                {
                    "urn": el.get("urn", self.current_textpart_urn),
                }
            )

            if len(self.element_stack) > 0:
                if (
                    len(
                        [
                            x
                            for x in self.element_stack[-1]["children"]
                            if x.get("index") == el["index"]
                        ]
                    )
                    == 0
                ):
                    self.elements.append(el)
            else:
                self.elements.append(el)

    def handle_div(self, attrs: dict):
        if attrs["type"] == "edition":
            self.lang = attrs["lang"]
            self.urn = attrs["n"]

        elif attrs["type"] == "textpart":
            self.add_textpart_to_stack(attrs)

    def handle_element(self, tagname: str, attrs: dict):
        textpart = None

        if len(self.textpart_stack) == 0:
            logger.warning(
                f"{self.urn}\nElements should not appear outside of textparts: {tagname}, {attrs}"
            )

            if len(self.textparts) > 0:
                textpart = self.textparts[-1]
        else:
            textpart = self.textpart_stack[-1]

        if textpart is None:
            logger.warning(
                f"{self.urn}\nOrphaned element: {tagname}, {attrs} — no textpart available."
            )
            return

        textpart_index = textpart["index"]
        urn_element_index = sum(
            [
                1
                for el in self.elements + self.element_stack
                if el["textpart_urn"] == self.current_textpart_urn
            ]
        )

        attrs.update(
            {
                "children": [],
                "index": len(self.element_stack) + len(self.elements),
                "tagname": tagname,
                "textpart_index": textpart_index,
                "textpart_urn": self.current_textpart_urn,
                "urn": f"{self.current_textpart_urn}@<{tagname}>[{urn_element_index}]",
            }
        )

        # If there is an unclosed element at the end of the stack,
        # add this element to its children.
        if len(self.element_stack) > 0:
            if self.element_stack[-1]["textpart_index"] != attrs["textpart_index"]:
                logger.warning(
                    f"{self.urn}\nOpen element belongs to a different textpart than current element: {self.element_stack[-1]}\n{attrs}"
                )
            self.element_stack[-1]["children"].append(attrs)

        self.element_stack.append(attrs)

    def process_tokens(self, tokens):
        text_run = []

        textpart = None
        if len(self.textpart_stack) > 0:
            textpart = self.textpart_stack[-1]

        for tok in tokens:
            if tok.text.strip() == "":
                continue

            if textpart is not None:
                urn_token_index = (
                    sum(
                        [1 for t in textpart.get("tokens", []) if t["text"] == tok.text]
                    )
                    + 1
                )
            else:
                urn_token_index = 1

            token = {
                "text": tok.text,
                "urn": f"{self.current_textpart_urn}@{tok.text}[{urn_token_index}]",
                "whitespace": len(tok.spaces_after) > 0,
            }

            if textpart is not None:
                if textpart.get("tokens") is not None:
                    textpart["tokens"].append(token)
                else:
                    textpart["tokens"] = [token]

            text_run.append(token)

        return {"tagname": "text_run", "tokens": text_run}

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
                logger.debug(
                    f"{self.urn}\nUnknown element {localname} in {self.current_textpart_urn}"
                )
                self.unhandled_elements.add(localname)
                self.handle_element(localname, clean_attrs)

    def tokenize(self, s: str):
        doc = None

        if self.lang == "grc":
            doc = greek_tokenizer(s)

        elif self.lang == "la":
            doc = latin_tokenizer(s)

        if doc is None:
            return []

        tokens = []
        for sentence in doc.sentences:  # pyright: ignore
            for token in sentence.tokens:
                tokens.append(token)

        return tokens


if __name__ == "__main__":
    import json

    handler = TEIParser("./data/tlg0530/tlg029/tlg0530.tlg029.verbatim-lat1.xml")

    with open("metadata.json", "w") as f:
        json.dump(
            create_table_of_contents(handler.textparts, handler.textpart_labels),
            f,
            ensure_ascii=False,
            indent=4,
        )

    with open("textparts.json", "w") as f:
        json.dump(handler.textparts, f, ensure_ascii=False, indent=4)

    with open("elements.json", "w") as f:
        json.dump(handler.elements, f, ensure_ascii=False, indent=4)
