"""
Levenshtein edit distance — pure Python, textdistance (zero C extensions).

Uses textdistance.Levenshtein(external=False) to guarantee the pure-Python
implementation is used regardless of whether jellyfish / editdistance are
installed on the system.

Usage:
    python levenshtein.py [path/to/pairs.tsv] [--json]
"""

import sys
import json
import time
from pathlib import Path

try:
    from textdistance import Levenshtein
except ImportError:
    sys.exit("textdistance not installed. Run: pip install textdistance")

JSON_MODE = "--json" in sys.argv
path_args = [a for a in sys.argv[1:] if not a.startswith("--")]

pairs_path = Path(path_args[0]) if path_args else \
             Path(__file__).parent.parent / "data" / "pairs_100k.tsv"

if not pairs_path.exists():
    sys.exit(f"File not found: {pairs_path}\nRun: python build_pairs.py")

def log(msg):
    if not JSON_MODE:
        print(msg, flush=True)

# Force pure-Python implementation — no jellyfish / editdistance C extensions.
algo = Levenshtein(external=False)

log(f"Loading pairs from: {pairs_path}")
lines = pairs_path.read_text(encoding="utf-8").splitlines()
log(f"Pairs: {len(lines):,}")

t0 = time.perf_counter()
checksum = 0

for line in lines:
    tab = line.find("\t")
    if tab < 0:
        continue
    a = line[:tab]
    b = line[tab + 1:]
    checksum += algo.distance(a, b)

elapsed_ms = (time.perf_counter() - t0) * 1000

if JSON_MODE:
    print(json.dumps({
        "pairs":      len(lines),
        "checksum":   checksum,
        "elapsed_ms": round(elapsed_ms, 1),
    }))
else:
    print(f"\nChecksum  : {checksum:,}")
    print(f"Elapsed   : {elapsed_ms:.1f} ms")
    print(f"Throughput: {len(lines) / (elapsed_ms / 1000):.0f} pairs/s")
