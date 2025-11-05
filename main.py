import json

from pathlib import Path

# from tools.gv_document import GVDocument
from tools.gv_sax_parser import GVSaxParser


if __name__ == "__main__":
    data_dir = Path("./data")
    out_dir = Path("./out")

    if not out_dir.exists():
        out_dir.mkdir()

    for subdir in [d for d in data_dir.iterdir() if d.is_dir()]:
        for subsubdir in [d for d in subdir.iterdir() if d.is_dir()]:
            for f in subsubdir.iterdir():
                if f.name.startswith("tlg"):
                    print(f)

                    new_filename = Path(f.name.replace(".xml", ".json"))

                    handler = GVSaxParser(f)

                    with open(out_dir / new_filename, "w") as g:
                        json.dump(handler.blocks, g, ensure_ascii=False, indent=2)
