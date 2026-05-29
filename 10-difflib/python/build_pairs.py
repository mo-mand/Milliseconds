"""
Generate integer-sequence pair datasets for diff benchmarking.

Each "document" is a sequence of integers (0-9999) representing line content
hashes. Modified versions have realistic line insertions, deletions, and
substitutions applied — same edit pattern as a code review diff.

Sequences are long enough (80-200 elements) to make LCS computation the
bottleneck rather than file I/O.

Format: one pair per line, tab-separated. Each side is comma-separated ints.

Outputs (in data/):
    pairs_10k.tsv    10 000 pairs
    pairs_50k.tsv    50 000 pairs
    pairs_100k.tsv  100 000 pairs

Usage:
    python build_pairs.py
"""

import random
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

rng = random.Random(42)
VOCAB = 9000  # unique "line" tokens

def rand_seq(length):
    return [rng.randint(0, VOCAB - 1) for _ in range(length)]

def mutate(seq):
    result = list(seq)
    n = len(result)
    # delete ~15%
    keep = sorted(rng.sample(range(n), k=max(1, int(n * 0.85))))
    result = [result[i] for i in keep]
    # substitute ~10%
    for i in rng.sample(range(len(result)), k=max(1, int(len(result) * 0.10))):
        result[i] = rng.randint(0, VOCAB - 1)
    # insert ~10%
    inserts = max(1, int(len(result) * 0.10))
    for _ in range(inserts):
        pos = rng.randint(0, len(result))
        result.insert(pos, rng.randint(0, VOCAB - 1))
    return result

TARGETS = {
    "pairs_10k.tsv":   10_000,
    "pairs_50k.tsv":   50_000,
    "pairs_100k.tsv": 100_000,
}

for name, n in TARGETS.items():
    out = DATA_DIR / name
    if out.exists():
        print(f"  {name} already exists -- skipping")
        continue
    rows = []
    for _ in range(n):
        length = rng.randint(80, 200)
        old = rand_seq(length)
        new = mutate(old)
        rows.append(",".join(map(str, old)) + "\t" + ",".join(map(str, new)))
    out.write_bytes(("\n".join(rows) + "\n").encode("utf-8"))
    print(f"  {name}: {n:,} pairs  ({out.stat().st_size // 1024:,} KB)")

print("\nDone.")
