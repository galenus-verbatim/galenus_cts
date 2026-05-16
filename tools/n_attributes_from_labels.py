"""
Set @n attributes on div[@type='textpart'][@subtype='section'] elements that lack them,
using the text content of their head or label[@type='head'] children.
"""

import sys
from pathlib import Path
from lxml import etree

TEI_NS = "http://www.tei-c.org/ns/1.0"
NS = {"tei": TEI_NS}


def elem_text(elem) -> str:
    return " ".join("".join(elem.itertext()).split())


def section_labels(section: etree._Element) -> list[etree._Element]:
    """Return head/label[@type='head'] elements belonging to this section,
    excluding those inside nested textpart sections."""
    results = []
    for elem in section:
        _collect_labels(elem, results)
    return results


def _collect_labels(elem: etree._Element, results: list) -> None:
    tag = etree.QName(elem.tag).localname if isinstance(elem.tag, str) else None
    if tag is None:
        return

    if tag == "div" and elem.get("subtype") == "section":
        return  # don't descend into nested sections

    if tag == "head":
        results.append(elem)
    elif tag == "label" and elem.get("type") == "head":
        results.append(elem)
    else:
        for child in elem:
            _collect_labels(child, results)


def choose_label(labels: list[etree._Element]) -> str:
    """Use the second label's text if there are multiple, else the first."""
    target = labels[1] if len(labels) > 1 else labels[0]
    return elem_text(target)


def process_file(path: Path) -> int:
    parser = etree.XMLParser(remove_blank_text=False)
    tree = etree.parse(path, parser)
    root = tree.getroot()

    sections = root.xpath(
        ".//tei:div[@type='textpart' and @subtype='section' and not(@n)]",
        namespaces=NS,
    )

    changed = 0
    for section in sections:
        labels = section_labels(section)
        if not labels:
            continue
        n_value = choose_label(labels)
        if n_value:
            section.set("n", n_value)
            changed += 1

    if changed:
        tree.write(path, xml_declaration=True, encoding="UTF-8", pretty_print=False)
        print(f"{path}: set @n on {changed} section(s)")
    else:
        print(f"{path}: nothing to change")

    return changed


def find_files(data_dir: Path) -> list[Path]:
    """Find all XML files under data_dir that contain section textparts without @n."""
    candidates = []
    for xml_file in sorted(data_dir.rglob("*.xml")):
        try:
            tree = etree.parse(xml_file, etree.XMLParser(remove_blank_text=False))
            hits = tree.getroot().xpath(
                ".//tei:div[@type='textpart' and @subtype='section' and not(@n)]",
                namespaces=NS,
            )
            if hits:
                candidates.append(xml_file)
        except etree.XMLSyntaxError:
            print(f"Skipping (parse error): {xml_file}", file=sys.stderr)
    return candidates


def main():
    project_root = Path(__file__).parent.parent
    data_dir = project_root / "data"

    if len(sys.argv) > 1:
        files = [Path(p) for p in sys.argv[1:]]
    else:
        print(f"Discovering files in {data_dir} …")
        files = find_files(data_dir)
        print(f"Found {len(files)} file(s) to process.\n")

    total = 0
    for path in files:
        total += process_file(path)
    print(f"\nTotal sections updated: {total}")


if __name__ == "__main__":
    main()
