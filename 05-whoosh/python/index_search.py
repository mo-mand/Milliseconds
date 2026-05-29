"""
Full-text search benchmark — pure Python, Whoosh (zero C extensions).

Phase 1: Index N documents from a JSONL file.
Phase 2: Run 1 000 queries against the index.

Usage:
    python index_search.py [path/to/docs.jsonl] [--json]
"""

import sys
import json
import time
import shutil
import tempfile
from pathlib import Path

try:
    import whoosh
    from whoosh import index
    from whoosh.fields import Schema, TEXT, ID
    from whoosh.qparser import QueryParser
    from whoosh.writing import AsyncWriter
except ImportError:
    sys.exit("whoosh not installed. Run: pip install whoosh")

JSON_MODE = "--json" in sys.argv
path_args = [a for a in sys.argv[1:] if not a.startswith("--")]

docs_path = Path(path_args[0]) if path_args else \
            Path(__file__).parent.parent / "data" / "docs_10k.jsonl"

if not docs_path.exists():
    sys.exit(f"File not found: {docs_path}\nRun: python build_corpus.py")

def log(msg):
    if not JSON_MODE:
        print(msg, flush=True)

schema = Schema(
    id    = ID(stored=True, unique=True),
    title = TEXT(stored=True),
    body  = TEXT(stored=False),
)

index_dir = tempfile.mkdtemp(prefix="whoosh_bench_")
try:
    # ---- Phase 1: Indexing --------------------------------------------------
    log(f"Indexing: {docs_path}")
    ix = index.create_in(index_dir, schema)
    writer = ix.writer(limitmb=256)

    lines = docs_path.read_text(encoding="utf-8").splitlines()
    docs  = [json.loads(l) for l in lines if l.strip()]

    t0 = time.perf_counter()
    for doc in docs:
        writer.add_document(id=doc["id"], title=doc["title"], body=doc["body"])
    writer.commit()
    index_ms = (time.perf_counter() - t0) * 1000

    log(f"Indexed {len(docs):,} docs in {index_ms:.1f} ms  "
        f"({len(docs) / (index_ms / 1000):.0f} docs/s)")

    # ---- Phase 2: Search ----------------------------------------------------
    searcher = ix.searcher()
    parser   = QueryParser("body", ix.schema)

    queries = [
        "government", "president", "market", "million", "company",
        "system", "national", "american", "police", "report",
        "official", "state", "party", "people", "program",
        "research", "university", "students", "science", "health",
    ]

    ROUNDS = 50   # 50 × 20 = 1 000 queries total
    total_hits = 0
    t1 = time.perf_counter()

    for _ in range(ROUNDS):
        for q in queries:
            results = searcher.search(parser.parse(q), limit=10)
            total_hits += len(results)

    search_ms     = (time.perf_counter() - t1) * 1000
    total_queries = ROUNDS * len(queries)

    log(f"Searched {total_queries:,} queries in {search_ms:.1f} ms  "
        f"({total_queries / (search_ms / 1000):.0f} queries/s)")
    log(f"Total hits: {total_hits:,}")

    searcher.close()

    if JSON_MODE:
        print(json.dumps({
            "docs":          len(docs),
            "index_ms":      round(index_ms, 1),
            "search_ms":     round(search_ms, 1),
            "total_queries": total_queries,
            "total_hits":    total_hits,
        }))

finally:
    shutil.rmtree(index_dir, ignore_errors=True)
