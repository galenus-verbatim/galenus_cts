"""Build the FTS5 full-text search index from kodon-db.sqlite.

Run with:
    uv run galenus-index
or:
    python -m galenus_site.build_search_index
"""

import sqlite3
import unicodedata
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
SRC_PATH = APP_DIR / "db" / "kodon-db.sqlite"
DST_PATH = APP_DIR / "static" / "search-index.sqlite"


def strip_diacritics(text: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", text)
        if unicodedata.category(c) != "Mn"
    ).lower()


def build(src_path: Path = SRC_PATH, dst_path: Path = DST_PATH) -> None:
    if dst_path.exists():
        dst_path.unlink()

    src = sqlite3.connect(f"file:{src_path}?mode=ro", uri=True)
    dst = sqlite3.connect(dst_path)
    dst.execute("PRAGMA journal_mode=OFF")
    dst.execute("PRAGMA synchronous=OFF")
    dst.execute("PRAGMA temp_store=MEMORY")
    dst.execute("PRAGMA cache_size=-64000")

    dst.execute("""
        CREATE TABLE textpart_meta (
            id   INTEGER PRIMARY KEY,
            urn  TEXT NOT NULL,
            document_urn TEXT NOT NULL,
            language     TEXT NOT NULL,
            title        TEXT NOT NULL,
            location     TEXT
        )
    """)
    # FTS4: sql.js does not ship with FTS5 enabled, so use FTS4 instead.
    # Searches return rowids which we join against textpart_meta.
    dst.execute("""
        CREATE VIRTUAL TABLE search_fts USING fts4(text)
    """)
    dst.commit()

    print("Fetching textpart metadata…")
    textparts = src.execute("""
        SELECT tp.id, tp.urn, tp.document_urn, d.language, d.title, tp.location
        FROM textparts tp
        JOIN documents d ON tp.document_urn = d.urn
        ORDER BY tp.id
    """).fetchall()
    print(f"  {len(textparts)} textparts")

    print("Grouping tokens by textpart…")
    token_rows = src.execute("""
        SELECT textpart_id, GROUP_CONCAT(text, ' ')
        FROM tokens
        GROUP BY textpart_id
        ORDER BY textpart_id
    """).fetchall()
    token_map = {row[0]: row[1] for row in token_rows}
    print(f"  {len(token_map)} textparts with tokens")

    print("Building index…")
    BATCH = 2000
    batch_meta: list = []
    batch_fts: list = []

    for tp_id, urn, doc_urn, lang, title, location in textparts:
        raw_text = token_map.get(tp_id, "")
        normalized = strip_diacritics(raw_text)
        batch_meta.append((tp_id, urn, doc_urn, lang, title, location))
        batch_fts.append((tp_id, normalized))

        if len(batch_meta) >= BATCH:
            dst.executemany("INSERT INTO textpart_meta VALUES (?,?,?,?,?,?)", batch_meta)
            dst.executemany("INSERT INTO search_fts(rowid, text) VALUES (?,?)", batch_fts)
            dst.commit()
            batch_meta.clear()
            batch_fts.clear()

    if batch_meta:
        dst.executemany("INSERT INTO textpart_meta VALUES (?,?,?,?,?,?)", batch_meta)
        dst.executemany("INSERT INTO search_fts(rowid, text) VALUES (?,?)", batch_fts)
        dst.commit()

    print("Optimizing FTS index…")
    dst.execute("INSERT INTO search_fts(search_fts) VALUES('optimize')")
    dst.commit()

    src.close()
    dst.close()

    size = dst_path.stat().st_size
    print(f"Done. {dst_path.name}  ({size / 1024 / 1024:.1f} MB)")


def main() -> None:
    import time
    t = time.time()
    build()
    print(f"Total: {time.time() - t:.1f}s")


if __name__ == "__main__":
    main()
