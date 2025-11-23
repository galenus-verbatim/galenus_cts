import json

from pathlib import Path

from tqdm import tqdm

# from tools.gv_document import GVDocument
from tools.gv_sax_parser import GVSaxParser
from tools.gv_lemmatizer import lemmatize_grc, lemmatize_lat


if __name__ == "__main__":
    data_dir = Path("./data")
    out_dir = Path("./out")

    if not out_dir.exists():
        out_dir.mkdir()

    unhandled_elements = set()
    files_to_process = []

    for subdir in [d for d in data_dir.iterdir() if d.is_dir()]:
        for subsubdir in [d for d in subdir.iterdir() if d.is_dir()]:
            for f in subsubdir.iterdir():
                if f.name.startswith("tlg"):
                    print(f)

                    files_to_process.append(f)

    for f in tqdm(files_to_process):
        work_urn_stub = f.name.replace(".xml", "")
        new_dir = Path(out_dir / work_urn_stub)

        if not new_dir.exists():
            new_dir.mkdir()

        new_filename = Path(f.name.replace(".xml", ".json"))

        handler = GVSaxParser(f)
        toc = handler.create_table_of_contents()
        textpart_labels = handler.textpart_labels

        for textpart in handler.textparts:
            lemmatized = []
            if "grc" in work_urn_stub:
                lemmatized = lemmatize_grc(textpart["text"])
            elif "lat" in work_urn_stub:
                lemmatized = lemmatize_lat(textpart["text"])
            else:
                raise Exception(f"Unknown language for {work_urn_stub}")

            textpart["lemmata"] = [t.lemma_ for t in lemmatized]
            textpart["tokens"] = [t.text for t in lemmatized]
            textpart["pos"] = [t.pos_ for t in lemmatized]

        with open(new_dir / new_filename, "w") as g:
            json.dump(
                {"elements": handler.elements, "textparts": handler.textparts},
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

        unhandled_elements.update(handler.unhandled_elements)

    with open("unhandled_elements.json", "w") as f:
        json.dump(list(unhandled_elements), f, ensure_ascii=False, indent=2)
