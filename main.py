import json

from pathlib import Path

from tqdm import tqdm

# from tools.gv_document import GVDocument
from tools.gv_sax_parser import GVSaxParser
from tools.gv_lemmatizer import nlp_grc, nlp_lat


class TextToken:
    def __init__(self, token, textpart_urn: str, urn_index: int) -> None:
        self.lemma = token.lemma_
        self.offset = token.idx
        self.pos = token.pos_
        self.text = token.text
        self.urn = f"{textpart_urn}@{token.text}[{urn_index}]"
        self.whitespace = token.whitespace_ or ""
        self.xml_id = f"word_index_{token.i}"
        self.end_offset = self.offset + len(self.text) + len(self.whitespace)

    def to_dict(self):
        return dict(
            end_offset=self.end_offset,
            lemma=self.lemma,
            offset=self.offset,
            pos=self.pos,
            text=self.text,
            urn=self.urn,
            whitespace=self.whitespace,
            xml_id=self.xml_id,
        )


def find_last(list_: list, fn):
    try:
        return next(x for x in list_[::-1] if fn(x))
    except StopIteration:
        return None


def parse_file(f: Path):
    new_filename = Path(f.name.replace(".xml", ".json"))

    handler = GVSaxParser(f)

    return handler, new_filename


def nest(nestable, parent=None, tree=None):
    if parent is None:
        parent = {"index": -1}

    if tree is None:
        tree = []

    children = [c for c in nestable if c["parent_index"] == parent["index"]]

    if parent["index"] == -1:
        tree = children
    else:
        parent["children"] = children  # pyright: ignore

    for child in children:
        nest(nestable, child, tree)

    return tree


def assign_parents(elements):
    for x in elements:
        candidates = [
            candidate
            for candidate in elements
            if candidate != x
            # prevent loops
            and candidate.get("parent_index") != x["index"]
            and candidate["offset"] != candidate["end_offset"]
            and candidate["offset"] <= x["offset"]
            and candidate["end_offset"] >= x["end_offset"]
        ]

        if len(candidates) == 0:
            # textparts shouldn't have parents
            if x.get("tagname") is None and x.get("type") == "textpart":
                x["parent_index"] = -1
            else:
                # print(
                #     f"No suitable parent for element at index {x['index']}, {x.get('tagname')}, {x.get('n')}"
                # )
                # but other elements should belong to the textpart
                x["parent_index"] = 0

        else:
            parent = min(candidates, key=lambda y: y["end_offset"] - y["offset"])

            x["parent_index"] = parent["index"]

            if x.get("urn") is None:
                x["urn"] = parent["urn"]

    return elements


def assign_tokens(elements, tokens):
    # tokens should always be contained by an element
    # in the textpart, not by the textpart itself
    for token in tokens:
        candidates = [
            el
            for el in elements
            if el["offset"] != el["end_offset"]
            and el["offset"] <= token["offset"]
            and el["end_offset"] >= token["end_offset"]
        ]

        if len(candidates) == 0:
            # print(f"Unable to find parent for token: {token}")
            # print("Finding nearest suitable parent")

            candidates = [
                el for el in elements if el["offset"] != el["end_offset"]
            ]

            if len(candidates) == 0:
                raise Exception(f"No parent found for {token}")

            parent = min(candidates, key=lambda x: abs(x["offset"] - token["offset"]))
        else:
            parent = min(candidates, key=lambda x: abs(x["end_offset"] - x["offset"]))

        if parent.get("tokens") is None:
            parent["tokens"] = []

        parent["tokens"].append(token)

    return elements


def build_tree(textpart, elements, lemmatized):
    tokens = [
        TextToken(
            t,
            textpart["urn"],
            [k.text for k in lemmatized[: t.i]].count(t.text) + 1,
        ).to_dict()
        for t in lemmatized
    ]

    for token in tokens:
        if token["urn"] == "urn:cts:greekLit:tlg0530.tlg029.verbatim-lat1:1@XVII[1]":
            print([t["text"] for t in tokens])
            print(textpart)
            raise Exception("What the heck is happening?")

    sorted_elements = sorted(elements, key=lambda x: x["index"])

    for i, x in enumerate(sorted_elements, 1):
        x["index"] = i

    sorted_elements = assign_tokens(sorted_elements, tokens)

    textpart["index"] = 0
    sorted_elements_with_textpart = assign_parents([textpart] + sorted_elements)

    return nest(sorted_elements_with_textpart)


def read_data_directory(data_dir: Path):
    return [Path("./data/tlg0530/tlg029/tlg0530.tlg029.verbatim-lat1.xml")]
    # files_to_process = []

    # for subdir in [d for d in data_dir.iterdir() if d.is_dir()]:
    #     for subsubdir in [d for d in subdir.iterdir() if d.is_dir()]:
    #         for f in subsubdir.iterdir():
    #             if f.name.startswith("tlg"):
    #                 print(f)

    #                 files_to_process.append(f)

    # return files_to_process


if __name__ == "__main__":
    data_dir = Path("./data")
    out_dir = Path("./out")

    if not out_dir.exists():
        out_dir.mkdir()

    unhandled_elements = set()
    files_to_process = read_data_directory(data_dir)

    for f in tqdm(files_to_process):
        new_dir = Path(out_dir / f.name.replace(".xml", ""))

        if not new_dir.exists():
            new_dir.mkdir()

        handler, new_filename = parse_file(f)
        outfile = Path(new_dir / new_filename)

        if outfile.exists():
            outfile.unlink()

        toc = handler.create_table_of_contents()
        textpart_labels = handler.textpart_labels
        work_urn_stub = f.name.replace(".xml", "")

        docs = []

        if "grc" in work_urn_stub:
            docs = nlp_grc([t["text"] for t in handler.textparts])
        elif "lat" in work_urn_stub:
            docs = nlp_lat([t["text"] for t in handler.textparts])
        else:
            raise Exception(f"Unknown language for {work_urn_stub}")

        textparts = []
        for lemmatized, textpart in zip(docs, handler.textparts):
            elements = [
                e for e in handler.elements if e["textpart_index"] == textpart["index"]
            ]

            del textpart["text"]

            tree = build_tree(textpart, elements, lemmatized)
            textparts.append(tree)

        with open(new_dir / new_filename, "w") as g:
            json.dump(
                {"textparts": textparts},
                g,
                ensure_ascii=False,
                indent=2,
            )

        with open(new_dir / "metadata.json", "w") as g:
            metadata = {
                "textpart_labels": textpart_labels,
                "table_of_contents": toc,
            }

            json.dump(metadata, g, ensure_ascii=False, indent=2)
