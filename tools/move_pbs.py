from copy import deepcopy
from pathlib import Path

from lxml import etree

DATA_PATH = Path(__file__).parent.parent.resolve() / "data"

TEI_NS = "http://www.tei-c.org/ns/1.0"
TEI = f"{{{TEI_NS}}}"

NS = {"tei": TEI_NS}


def is_textpart(el):
    return el.tag == f"{TEI}div" and el.get("type") == "textpart"


def in_textpart(el):
    ancestor = el.getparent()
    while ancestor is not None:
        if is_textpart(ancestor):
            return True
        ancestor = ancestor.getparent()
    return False


def first_leaf_textpart(div):
    """Return the first leaf-node textpart within div."""
    children_textparts = [c for c in div if is_textpart(c)]
    if not children_textparts:
        return div
    return first_leaf_textpart(children_textparts[0])


def last_leaf_textpart(div):
    """Return the last leaf-node textpart within div."""
    children_textparts = [c for c in div if is_textpart(c)]
    if not children_textparts:
        return div
    return last_leaf_textpart(children_textparts[-1])


def move_pb(pb):
    parent = pb.getparent()
    siblings = list(parent)
    idx = siblings.index(pb)

    next_textpart = next(
        (s for s in siblings[idx + 1 :] if is_textpart(s)), None
    )
    prev_textpart = next(
        (s for s in reversed(siblings[:idx]) if is_textpart(s)), None
    )

    if next_textpart is None and prev_textpart is None:
        print(f"  WARNING: no adjacent textpart found for {etree.tostring(pb)}")
        return

    parent.remove(pb)

    if next_textpart is not None and prev_textpart is not None:
        # Between two textparts: copy into the last leaf of prev and first leaf of next
        last_leaf_textpart(prev_textpart).append(deepcopy(pb))
        first_leaf_textpart(next_textpart).insert(0, pb)
    elif next_textpart is not None:
        first_leaf_textpart(next_textpart).insert(0, pb)
    else:
        last_leaf_textpart(prev_textpart).append(pb)


def process_file(path):
    tree = etree.parse(path)
    root = tree.getroot()

    pbs_outside = [
        pb for pb in root.findall(".//tei:pb", NS) if not in_textpart(pb)
    ]

    if not pbs_outside:
        return False

    print(f"{path.name}: moving {len(pbs_outside)} pb element(s)")
    for pb in pbs_outside:
        move_pb(pb)

    tree.write(path, xml_declaration=True, encoding="UTF-8", pretty_print=True)
    return True


def main():
    xml_files = [
        p
        for p in DATA_PATH.rglob("*.xml")
        if p.name != "__cts__.xml"
    ]

    changed = 0
    for path in sorted(xml_files):
        if process_file(path):
            changed += 1

    print(f"\nDone. Modified {changed} file(s).")


if __name__ == "__main__":
    main()
