from pathlib import Path
from lxml import etree
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

NAMESPACES = {"tei": "http://www.tei-c.org/ns/1.0"}


@dataclass
class TextPartNode:
    """Represents a textpart in the document hierarchy."""

    n: str
    level: int
    content: List[Dict[str, Any]]
    children: List["TextPartNode"]
    parent: Optional["TextPartNode"] = None
    is_auto_numbered: bool = False  # Track if 'n' was auto-generated

    def get_path(self) -> List[str]:
        """Get the full path from root to this node."""
        path = []
        current = self
        while current:
            path.insert(0, current.n)
            current = current.parent
        return path

    def get_urn_suffix(self) -> str:
        """Get the URN suffix for this textpart."""
        return ".".join(self.get_path())


class GVDocument:
    def __init__(self, filename: Path):
        self.filename = str(filename)
        self.tree = etree.parse(filename)
        self.urn = f"urn:cts:greekLit:{filename.name.replace('.xml', '')}"
        self.levels = self.read_refsDecl()
        self.num_levels = len(self.levels)
        self.textpart_tree = self.build_textpart_tree()
        self.pages = self.get_pages()
        self.toc = self.build_toc()

    def read_refsDecl(self) -> List[str]:
        """Read the reference declaration to determine textpart levels."""
        refsDecl = self.tree.find(".//tei:refsDecl[@n='CTS']", namespaces=NAMESPACES)

        assert refsDecl is not None, f"No refsDecl element found for {self.urn}"

        return list(
            reversed(
                [
                    ref.get("n", "")
                    for ref in refsDecl.iterfind(
                        "./tei:cRefPattern", namespaces=NAMESPACES
                    )
                ]
            )
        )

    def build_textpart_tree(self) -> List[TextPartNode]:
        """Build a hierarchical tree of textparts."""
        root_textparts = []
        # Track counters per parent and subtype: {parent_id: {subtype: count}}
        subtype_counters = {}

        # Get all textparts with XPath
        all_textparts = self.tree.findall(
            ".//tei:div[@type='textpart']", namespaces=NAMESPACES
        )

        # Build tree structure
        for textpart_elem in all_textparts:
            # Determine level by counting textpart ancestors
            level = len(
                textpart_elem.xpath(
                    "ancestor::tei:div[@type='textpart']", namespaces=NAMESPACES
                )
            )

            # Get or generate 'n' attribute
            n_value = textpart_elem.get("n")
            is_auto = False

            if n_value is None:
                is_auto = True
                subtype = textpart_elem.get("subtype", "section")

                # Find parent to create unique counter key
                parent_elem = textpart_elem.xpath(
                    "parent::tei:div[@type='textpart']", namespaces=NAMESPACES
                )

                if parent_elem:
                    # Use parent element's id for uniqueness
                    parent_id = id(parent_elem[0])
                else:
                    parent_id = "root"

                # Initialize parent's counter dict if needed
                if parent_id not in subtype_counters:
                    subtype_counters[parent_id] = {}

                # Increment counter for this subtype under this parent
                if subtype not in subtype_counters[parent_id]:
                    subtype_counters[parent_id][subtype] = 0
                subtype_counters[parent_id][subtype] += 1

                n_value = str(subtype_counters[parent_id][subtype])

            # Extract content from this textpart's direct p elements
            content = []
            for p in textpart_elem.findall("./tei:p", namespaces=NAMESPACES):
                content.extend(self.get_children(p))

            node = TextPartNode(
                n=n_value,
                level=level,
                content=content,
                children=[],
                is_auto_numbered=is_auto,
            )

            # Find parent
            parent_elem = textpart_elem.xpath(
                "parent::tei:div[@type='textpart']", namespaces=NAMESPACES
            )

            if parent_elem:
                # Find parent node and add this as child
                parent_n = self._get_or_generate_parent_n(
                    parent_elem[0], subtype_counters
                )
                parent_node = self._find_node_by_n(root_textparts, parent_n)
                if parent_node:
                    node.parent = parent_node
                    parent_node.children.append(node)
            else:
                # This is a root textpart
                root_textparts.append(node)

        return root_textparts

    def _find_node_by_n(
        self, nodes: List[TextPartNode], n: str
    ) -> Optional[TextPartNode]:
        """Recursively find a node by its 'n' attribute."""
        for node in nodes:
            if node.n == n:
                return node
            found = self._find_node_by_n(node.children, n)
            if found:
                return found
        return None

    def _get_or_generate_parent_n(self, parent_elem, subtype_counters: Dict) -> str:
        """Get the n attribute of a parent element, generating if necessary."""
        n_value = parent_elem.get("n")
        if n_value is not None:
            return n_value

        # Need to generate based on subtype
        subtype = parent_elem.get("subtype", "section")

        # Find grandparent
        grandparent = parent_elem.xpath(
            "parent::tei:div[@type='textpart']", namespaces=NAMESPACES
        )

        if grandparent:
            grandparent_id = id(grandparent[0])
        else:
            grandparent_id = "root"

        # Initialize if needed
        if grandparent_id not in subtype_counters:
            subtype_counters[grandparent_id] = {}

        # Count preceding siblings with same subtype
        preceding_same_subtype = parent_elem.xpath(
            f"preceding-sibling::tei:div[@type='textpart' and @subtype='{subtype}']",
            namespaces=NAMESPACES,
        )

        return str(len(preceding_same_subtype) + 1)

    def get_pages(self) -> List[Dict[str, Any]]:
        """Get all pages (deepest level textparts) for pagination."""
        pages = []
        self._collect_deepest_textparts(self.textpart_tree, pages)
        return pages

    def _collect_deepest_textparts(
        self, nodes: List[TextPartNode], pages: List[Dict[str, Any]]
    ):
        """Recursively collect the deepest textparts for pagination."""
        for node in nodes:
            if not node.children:
                # This is a leaf node (deepest level)
                pages.append(
                    {
                        "n": node.n,
                        "urn": f"{self.urn}:{node.get_urn_suffix()}",
                        "path": node.get_path(),
                        "level": node.level,
                        "content": node.content,
                    }
                )
            else:
                # Continue recursing
                self._collect_deepest_textparts(node.children, pages)

    def build_toc(self) -> List[Dict[str, Any]]:
        """Build a table of contents from the textpart hierarchy."""
        return [self._node_to_toc_entry(node) for node in self.textpart_tree]

    def _node_to_toc_entry(self, node: TextPartNode) -> Dict[str, Any]:
        """Convert a textpart node to a TOC entry."""
        entry = {
            "n": node.n,
            "level": node.level,
            "label": self.levels[node.level]
            if node.level < len(self.levels)
            else "section",
            "urn": f"{self.urn}:{node.get_urn_suffix()}",
            "path": node.get_path(),
            "has_content": len(node.content) > 0,
            "children": [self._node_to_toc_entry(child) for child in node.children],
        }
        return entry

    def get_page_by_reference(self, ref: str) -> Optional[Dict[str, Any]]:
        """Get a page by its reference (e.g., '1.2.3')."""
        parts = ref.split(".")
        for page in self.pages:
            if page["path"] == parts:
                return page
        return None

    def get_page_index(self, ref: str) -> Optional[int]:
        """Get the index of a page by its reference."""
        parts = ref.split(".")
        for i, page in enumerate(self.pages):
            if page["path"] == parts:
                return i
        return None

    def get_navigation_context(self, page_index: int) -> Dict[str, Any]:
        """Get navigation context for a page (prev, next, parent sections)."""
        current_page = self.pages[page_index]

        context = {
            "current": current_page,
            "prev": self.pages[page_index - 1] if page_index > 0 else None,
            "next": self.pages[page_index + 1]
            if page_index < len(self.pages) - 1
            else None,
            "ancestors": self._get_ancestors(current_page["node"]),
            "total_pages": len(self.pages),
            "current_index": page_index,
        }

        return context

    def _get_ancestors(self, node: TextPartNode) -> List[Dict[str, Any]]:
        """Get all ancestors of a node for breadcrumb navigation."""
        ancestors = []
        current = node.parent
        while current:
            ancestors.insert(
                0,
                {
                    "n": current.n,
                    "level": current.level,
                    "label": self.levels[current.level]
                    if current.level < len(self.levels)
                    else "section",
                    "urn": f"{self.urn}:{current.get_urn_suffix()}",
                },
            )
            current = current.parent
        return ancestors

    def get_children(self, p) -> List[Dict[str, Any]]:
        """Parse children of a paragraph element."""
        return [self._handle_child(child) for child in p.iterchildren()]

    def _handle_child(self, child) -> Dict[str, Any]:
        """Handle individual child elements."""
        if child.get("n") is not None:
            return {
                "attributes": dict(child.attrib),
                "subtype": etree.QName(child.tag).localname,
                "content": child.tail if child.tail else "",
                "type": "text_element",
            }
        else:
            subtype = "comment"

            try:
                subtype = etree.QName(child.tag).localname
            except ValueError:
                print(f"Encountered a weird tag: {child.tag}")

            return {
                "attributes": dict(child.attrib),
                "subtype": subtype,
                "content": etree.tostring(child, encoding="unicode", with_tail=True),
                "type": "text_element",
            }

    def print_structure(self):
        """Print the document structure for debugging."""
        print(f"Document: {self.urn}")
        print(f"Levels: {self.levels} ({self.num_levels} levels)")
        print(f"Total pages: {len(self.pages)}")
        print("\nTable of Contents:")
        self._print_toc(self.toc, indent=0)

    def _print_toc(self, toc_entries: List[Dict[str, Any]], indent: int):
        """Recursively print TOC entries."""
        for entry in toc_entries:
            prefix = "  " * indent
            print(f"{prefix}- {entry['label']} {entry['n']} (level {entry['level']})")
            if entry["children"]:
                self._print_toc(entry["children"], indent + 1)


# Example usage
if __name__ == "__main__":
    # Example with a document
    doc = GVDocument(Path("your_document.xml"))

    # Print document structure
    doc.print_structure()

    # Access pages
    print(f"\nFirst page URN: {doc.pages[0]['urn']}")

    # Get navigation for a specific page
    nav = doc.get_navigation_context(0)
    print("\nNavigation context for first page:")
    print(f"  Previous: {nav['prev']['urn'] if nav['prev'] else 'None'}")
    print(f"  Next: {nav['next']['urn'] if nav['next'] else 'None'}")
    print(f"  Ancestors: {[a['label'] + ' ' + a['n'] for a in nav['ancestors']]}")

    # Get specific page by reference
    page = doc.get_page_by_reference("1.2")
    if page:
        print(f"\nPage 1.2 URN: {page['urn']}")
