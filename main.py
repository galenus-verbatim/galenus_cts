import json

from pathlib import Path

# from tools.gv_document import GVDocument
from tools.gv_sax_parser import GVSaxParser


if __name__ == "__main__":
    data_dir = Path("./data")
    out_dir = Path("./out")

    if not out_dir.exists():
        out_dir.mkdir()

    unhandled_elements = set()
    for subdir in [d for d in data_dir.iterdir() if d.is_dir()]:
        for subsubdir in [d for d in subdir.iterdir() if d.is_dir()]:
            for f in subsubdir.iterdir():
                if f.name.startswith("tlg"):
                    print(f)

                    work_urn_stub = f.name.replace(".xml", "")
                    new_dir = Path(out_dir / work_urn_stub)

                    if not new_dir.exists():
                        new_dir.mkdir()

                    new_filename = Path(f.name.replace(".xml", ".json"))

                    handler = GVSaxParser(f)

                    with open(new_dir / new_filename, "w") as g:
                        json.dump(handler.blocks, g, ensure_ascii=False, indent=2)

                    with open(new_dir / "metadata.json", "w") as g:
                        json.dump(handler.create_table_of_contents(), g, ensure_ascii=False, indent=2)

                    unhandled_elements.update(handler.unhandled_elements)


    with open("unhandled_elements.json", "w") as f:
        json.dump(list(unhandled_elements), f, ensure_ascii=False, indent=2)
