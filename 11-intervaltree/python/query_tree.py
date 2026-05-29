"""
Interval tree benchmark - pure Python, intervaltree library.

Builds an IntervalTree from N intervals then runs Q point queries,
summing hit counts as the validation checksum.

Usage:
    python query_tree.py [path/to/data.tsv] [--json]
"""

import sys
import json
import time
from pathlib import Path

try:
    from intervaltree import IntervalTree
except ImportError:
    sys.exit("intervaltree not installed. Run: pip install intervaltree")

JSON_MODE = "--json" in sys.argv
path_args = [a for a in sys.argv[1:] if not a.startswith("--")]

data_path = Path(path_args[0]) if path_args else \
            Path(__file__).parent.parent / "data" / "data_100k.tsv"

if not data_path.exists():
    sys.exit(f"File not found: {data_path}\nRun: python build_data.py")

def log(msg):
    if not JSON_MODE:
        print(msg, flush=True)

lines = data_path.read_text(encoding="utf-8").splitlines()
sep = lines.index("")
intervals = [tuple(map(int, l.split("\t"))) for l in lines[:sep]]
queries   = list(map(int, lines[sep+1:]))
log(f"Intervals: {len(intervals):,}  Queries: {len(queries):,}")

# ---- Build ------------------------------------------------------------------
t_build = time.perf_counter()
tree = IntervalTree()
for i, (begin, end) in enumerate(intervals):
    # addi uses [begin, end) exclusive end; pass end+1 to get inclusive [begin, end].
    # Unique data tag prevents intervaltree from deduplicating identical (begin,end) pairs.
    tree.addi(begin, end + 1, i)
build_ms = (time.perf_counter() - t_build) * 1000

# ---- Query ------------------------------------------------------------------
t_query = time.perf_counter()
checksum = 0
for q in queries:
    checksum += len(tree.at(q))
query_ms = (time.perf_counter() - t_query) * 1000

if JSON_MODE:
    print(json.dumps({
        "intervals": len(intervals),
        "queries":   len(queries),
        "checksum":  checksum,
        "build_ms":  round(build_ms, 1),
        "query_ms":  round(query_ms, 1),
        "elapsed_ms": round(build_ms + query_ms, 1),
    }))
else:
    print(f"\nChecksum  : {checksum:,}")
    print(f"Build     : {build_ms:.1f} ms")
    print(f"Query     : {query_ms:.1f} ms")
    print(f"Throughput: {len(queries) / (query_ms / 1000):.0f} queries/s")
