import json

from pathlib import Path

from tools.galenus_verbatim import GVDocument


if __name__ == "__main__":
    data_dir = Path("./data")
    out_dir = Path("./out")

    if not out_dir.exists():
        out_dir.mkdir()

    for subdir in [d for d in data_dir.iterdir() if d.is_dir()]:
        for subsubdir in [d for d in subdir.iterdir() if d.is_dir()]:
            for f in subsubdir.iterdir():
                if f.name.startswith("tlg"):
                    gv_doc = GVDocument(f)
                    new_filename = Path(f.name.replace(".xml", ".json"))

                    with open(out_dir / new_filename, "w") as g:
                        json.dump(
                            {
                                "urn": gv_doc.urn,
                                "filename": gv_doc.filename,
                                "chapters": gv_doc.chapters,
                            },
                            g,
                            ensure_ascii=False
                        )

    # gv_doc = GVDocument("./data/tlg0057/tlg001/tlg0057.tlg001.1st1K-grc1.xml")

    # print(gv_doc.chapters)
