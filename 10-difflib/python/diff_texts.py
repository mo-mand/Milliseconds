"""
Sequence diff benchmark - pure Python, difflib.SequenceMatcher.

Diffs pairs of integer sequences (simulating line-hash diffs) and counts
insertions, deletions, and equal runs as the checksum.

Usage:
    python diff_texts.py [path/to/pairs.tsv] [--json]
"""

import sys
import json
import time
import difflib
from pathlib import Path

JSON_MODE = "--json" in sys.argv
path_args = [a for a in sys.argv[1:] if not a.startswith("--")]

pairs_path = Path(path_args[0]) if path_args else \
             Path(__file__).parent.parent / "data" / "pairs_10k.tsv"

if not pairs_path.exists():
    sys.exit(f"File not found: {pairs_path}\nRun: python build_pairs.py")

def log(msg):
    if not JSON_MODE:
        print(msg, flush=True)

log(f"Loading pairs from: {pairs_path}")
raw = pairs_path.read_text(encoding="utf-8").splitlines()

# pre-parse into lists of ints
pairs = []
for line in raw:
    tab = line.find("\t")
    if tab < 0:
        continue
    a = list(map(int, line[:tab].split(",")))
    b = list(map(int, line[tab+1:].split(",")))
    pairs.append((a, b))

log(f"Pairs: {len(pairs):,}")

t0 = time.perf_counter()
insertions = 0
deletions  = 0
unchanged  = 0

for a, b in pairs:
    matcher = difflib.SequenceMatcher(None, a, b, autojunk=False)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            unchanged += (i2 - i1)
        elif tag == "insert":
            insertions += (j2 - j1)
        elif tag == "delete":
            deletions += (i2 - i1)
        elif tag == "replace":
            deletions  += (i2 - i1)
            insertions += (j2 - j1)

elapsed_ms = (time.perf_counter() - t0) * 1000
checksum = insertions + deletions

if JSON_MODE:
    print(json.dumps({
        "pairs":      len(pairs),
        "insertions": insertions,
        "deletions":  deletions,
        "unchanged":  unchanged,
        "checksum":   checksum,
        "elapsed_ms": round(elapsed_ms, 1),
    }))
else:
    print(f"\nInsertions : {insertions:,}")
    print(f"Deletions  : {deletions:,}")
    print(f"Unchanged  : {unchanged:,}")
    print(f"Elapsed    : {elapsed_ms:.1f} ms")
    print(f"Throughput : {len(pairs) / (elapsed_ms / 1000):.0f} pairs/s")
