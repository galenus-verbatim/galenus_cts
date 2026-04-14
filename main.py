import sys
from pathlib import Path

from lxml import etree

TEI_NS = "http://www.tei-c.org/ns/1.0"
NS = {"tei": TEI_NS}

DATA_DIR = Path("data")
XML_FILES = DATA_DIR.glob("./**/tlg*.xml")

# Elements to move into the next deepest citation div when found outside one
ELEMENTS_TO_MOVE = frozenset({"milestone", "pb", "head", "p"})


def local_name(el) -> str:
    """Return the local tag name, or '' for non-element nodes (comments, PIs)."""
    if callable(el.tag):
        return ""
    return etree.QName(el.tag).localname


def get_deepest_citation_subtype(root) -> str | None:
    """
    Read the first (most specific) cRefPattern from the CTS refsDecl and
    return its n= value (e.g. 'chapter', 'section').  Returns None when no
    CTS refsDecl is present.
    """
    refs = root.findall(".//tei:refsDecl[@n='CTS']/tei:cRefPattern", NS)
    if not refs:
        return None
    return refs[0].get("n")


def get_leaf_citation_divs(root, deepest_subtype: str) -> list:
    """
    Find all div[@type='textpart'] that have no div[@type='textpart'] children.
    These are the "leaf" (deepest actual) citation divs in the document.

    If the deepest_subtype from the refsDecl matches a subtype present in the
    tree, restrict to divs with that subtype so that mismatches between the
    refsDecl name and the actual subtype attribute don't cause problems.
    """
    all_tp = root.findall('.//tei:div[@type="textpart"]', NS)
    if not all_tp:
        return []

    # Check whether the refsDecl subtype name actually appears in the tree.
    actual_subtypes = {d.get("subtype") for d in all_tp}
    if deepest_subtype in actual_subtypes:
        candidates = [d for d in all_tp if d.get("subtype") == deepest_subtype]
    else:
        # Fall back to true leaf divs (no textpart children).
        candidates = [
            d for d in all_tp if not d.findall('tei:div[@type="textpart"]', NS)
        ]

    return candidates


def process_container(container, filepath: Path) -> bool:
    """
    Within `container`, find direct-child <milestone>, <pb>, and <head>
    elements (i.e. those sitting outside any div[@type='textpart']) and move
    each accumulated batch into the *beginning* of the next sibling
    div[@type='textpart'].

    Logs any other unexpected direct children.

    Returns True when the tree was modified.
    """
    children = list(container)  # snapshot before any mutation
    buffer: list = []
    citation_divs_seen: list = []
    modified = False

    for child in children:
        tag = local_name(child)
        if not tag:
            # Comment or processing instruction — leave in place.
            continue

        if tag == "div" and child.get("type") == "textpart":
            citation_divs_seen.append(child)
            if buffer:
                # Prepend buffered elements in their original order.
                for el in reversed(buffer):
                    child.insert(0, el)
                print(
                    f"  moved {len(buffer)} element(s) into <div n='{child.get('n')}'>",
                    file=sys.stderr,
                )
                buffer.clear()
                modified = True

        elif tag in ELEMENTS_TO_MOVE:
            container.remove(child)
            buffer.append(child)

        else:
            print(
                f"LOG {filepath}: <{tag}> outside deepest citation divs"
                f" (attrs: {dict(child.attrib)})",
                file=sys.stderr,
            )

    # Handle elements that trail after all citation divs.
    if buffer:
        if citation_divs_seen:
            last_div = citation_divs_seen[-1]
            for el in buffer:
                last_div.append(el)
            print(
                f"  WARNING {filepath}: {len(buffer)} trailing element(s) "
                f"appended to end of last citation div "
                f"(n='{last_div.get('n')}')",
                file=sys.stderr,
            )
            modified = True
        else:
            # Nowhere to move them — re-attach and report.
            for el in buffer:
                container.append(el)
            print(
                f"  WARNING {filepath}: {len(buffer)} element(s) to move "
                f"but no citation divs found — left in place",
                file=sys.stderr,
            )

    return modified


def move_elements_within_textparts():
    for xml_path in sorted(DATA_DIR.glob("./**/tlg*.xml")):
        tree = etree.parse(str(xml_path))
        root = tree.getroot()

        deepest_subtype = get_deepest_citation_subtype(root)
        if deepest_subtype is None:
            print(f"WARNING {xml_path}: no CTS refsDecl found", file=sys.stderr)
            continue

        leaf_divs = get_leaf_citation_divs(root, deepest_subtype)
        if not leaf_divs:
            print(f"WARNING {xml_path}: no citation divs found", file=sys.stderr)
            continue

        # Collect the unique parent elements of the leaf citation divs.
        # Use a dict to preserve document order while deduplicating.
        parent_containers: dict = {}
        for div in leaf_divs:
            parent = div.getparent()
            if parent is not None:
                parent_containers[id(parent)] = parent

        file_modified = False
        for container in parent_containers.values():
            if process_container(container, xml_path):
                file_modified = True

        if file_modified:
            tree.write(
                str(xml_path),
                xml_declaration=True,
                encoding="UTF-8",
                pretty_print=False,
            )
            print(f"saved {xml_path}", file=sys.stderr)


if __name__ == "__main__":
    move_elements_within_textparts()
