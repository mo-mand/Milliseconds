"""
Generate interval + query datasets.

Each interval is [begin, end] with begin <= end drawn from [0, 1_000_000].
Average interval length ~50_000 so queries have a realistic number of hits.

File format:
    begin<TAB>end
    ... (N interval lines)
    (blank line)
    query_point
    ... (Q query lines)

Outputs (in data/):
    data_100k.tsv    100 000 intervals + 50 000 queries
    data_500k.tsv    500 000 intervals + 50 000 queries
    data_1m.tsv    1 000 000 intervals + 50 000 queries

Usage:
    python build_data.py
"""

import random
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

rng = random.Random(42)
SPACE   = 1_000_000
AVG_LEN = 1_000   # ~0.1% hit rate per query → manageable result sets
QUERIES = 10_000

def rand_interval():
    a = rng.randint(0, SPACE)
    length = int(rng.expovariate(1 / AVG_LEN))
    b = min(a + length, SPACE)
    return a, b

TARGETS = {
    "data_100k.tsv":   100_000,
    "data_500k.tsv":   500_000,
    "data_1m.tsv":   1_000_000,
}

query_pts = [rng.randint(0, SPACE) for _ in range(QUERIES)]

for name, n in TARGETS.items():
    out = DATA_DIR / name
    if out.exists():
        print(f"  {name} already exists -- skipping")
        continue
    lines = []
    for _ in range(n):
        a, b = rand_interval()
        lines.append(f"{a}\t{b}")
    lines.append("")
    lines.extend(map(str, query_pts))
    out.write_bytes(("\n".join(lines) + "\n").encode("utf-8"))
    print(f"  {name}: {n:,} intervals + {QUERIES:,} queries  ({out.stat().st_size // 1024:,} KB)")

print("\nDone.")
