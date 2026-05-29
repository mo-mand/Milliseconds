"""
Download the Stanford SNAP Wikipedia link graph and convert to links.tsv.

Dataset: enwiki-2013  (4,206,785 nodes, 101,355,853 edges)
Source  : https://snap.stanford.edu/data/wiki-topcats.html

Outputs: data/links.tsv   (tab-separated fromId<TAB>toId, one edge per line)

Usage:
    python download_data.py [--small]

    --small   downloads the smaller wiki-vote graph (~7 k nodes, 100 k edges)
              good for a quick smoke-test before running the full dataset.
"""

import sys
import gzip
import urllib.request
from pathlib import Path

SMALL = "--small" in sys.argv

if SMALL:
    URL  = "https://snap.stanford.edu/data/wiki-Vote.txt.gz"
    NAME = "wiki-vote"
else:
    # wiki-topcats: 1.8 M nodes, 28.5 M edges (more manageable than enwiki-2013)
    URL  = "https://snap.stanford.edu/data/wiki-topcats.txt.gz"
    NAME = "wiki-topcats"

DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

gz_path  = DATA_DIR / f"{NAME}.txt.gz"
tsv_path = DATA_DIR / "links.tsv"

# ---- Download ---------------------------------------------------------------
if not gz_path.exists():
    print(f"Downloading {NAME} ...")
    urllib.request.urlretrieve(URL, gz_path)
    print(f"Saved: {gz_path}  ({gz_path.stat().st_size / 1_048_576:.1f} MB)")
else:
    print(f"Already downloaded: {gz_path}")

# ---- Convert to TSV ---------------------------------------------------------
print(f"Converting to {tsv_path} ...")
edges = 0
with gzip.open(gz_path, "rt", encoding="utf-8") as src, open(tsv_path, "w", encoding="utf-8") as dst:
    for line in src:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) != 2:
            continue
        dst.write(f"{parts[0]}\t{parts[1]}\n")
        edges += 1

print(f"Done. {edges:,} edges written to {tsv_path}")
print()
print("Next steps:")
print("  python python/pagerank.py          # run Python baseline")
print("  dotnet run -c Release --project dotnet/PageRank.csproj   # run .NET")
