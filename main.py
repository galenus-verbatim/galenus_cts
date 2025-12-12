import json
import logging

from pathlib import Path

from tqdm import tqdm

from tools.tei_parser import TEIParser, create_table_of_contents, nlp_grc, nlp_lat

logger = logging.getLogger(__name__)


def parse_file(f: Path):
    handler = TEIParser(f)

    return handler


def read_data_directory(data_dir: Path):
    files_to_process = []

    for subdir in [d for d in data_dir.iterdir() if d.is_dir()]:
        for subsubdir in [d for d in subdir.iterdir() if d.is_dir()]:
            for f in subsubdir.iterdir():
                if f.name.startswith("tlg"):
                    print(f)

                    files_to_process.append(f)

    return files_to_process


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

        handler = parse_file(f)
        toc = create_table_of_contents(handler.textparts, handler.textpart_labels)

        elements_file = Path(new_dir / f.name.replace(".xml", ".elements.json"))
        textparts_file = Path(new_dir / f.name.replace(".xml", ".textparts.json"))

        with open(elements_file, "w") as g:
            json.dump(handler.elements, g, ensure_ascii=False, indent=2)

        with open(textparts_file, "w") as g:
            json.dump(
                handler.textparts,
                g,
                ensure_ascii=False,
                indent=2,
            )

        with open(new_dir / "metadata.json", "w") as g:
            metadata = {
                "textpart_labels": handler.textpart_labels,
                "table_of_contents": toc,
            }

            json.dump(metadata, g, ensure_ascii=False, indent=2)
