"""
Build corpus slices for the tokenizer benchmark using NLTK's built-in
corpora (Gutenberg + Brown + Reuters) — no external S3 download needed.

The combined raw text (~4 MB) is tiled to produce slices of 10 MB,
50 MB, and 100 MB.  Tiling does not affect tokenization speed measurements
because the same token distribution repeats, making the results stable.

Usage:
    python download_data.py
"""

import sys
import nltk
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

# ---- Download NLTK corpora --------------------------------------------------
PACKAGES = ["gutenberg", "brown", "reuters", "punkt", "punkt_tab"]
print("Downloading NLTK corpora ...")
for pkg in PACKAGES:
    try:
        nltk.download(pkg, quiet=True)
        print(f"  {pkg} OK")
    except Exception as e:
        print(f"  {pkg} WARN: {e}")

# ---- Collect all raw text ---------------------------------------------------
print("\nCollecting text ...")
chunks = []

from nltk.corpus import gutenberg, brown, reuters

for fid in gutenberg.fileids():
    chunks.append(gutenberg.raw(fid))
    print(f"  gutenberg/{fid}: {len(chunks[-1])//1024} KB")

for cat in brown.categories():
    chunks.append(brown.raw(categories=cat))
print(f"  brown corpus: {sum(len(brown.raw(categories=c)) for c in brown.categories())//1024} KB")

for fid in list(reuters.fileids())[:500]:     # first 500 articles
    chunks.append(reuters.raw(fid))
print(f"  reuters (500 articles): {sum(len(reuters.raw(f)) for f in list(reuters.fileids())[:500])//1024} KB")

base_text = "\n\n".join(chunks)
base_mb   = len(base_text) / 1_048_576
print(f"\nBase corpus: {base_mb:.1f} MB")

# ---- Tile to target sizes ---------------------------------------------------
MB = 1_048_576
TARGETS = {"corpus_10mb.txt": 10, "corpus_50mb.txt": 50, "corpus_100mb.txt": 100}

print("Writing slices ...")
for name, target_mb in TARGETS.items():
    out = DATA_DIR / name
    if out.exists():
        print(f"  {name} already exists ({out.stat().st_size // MB} MB)")
        continue
    target_bytes = target_mb * MB
    # Tile the base text until we reach the target size.
    reps   = (target_bytes // len(base_text)) + 2
    tiled  = (base_text * reps)[:target_bytes]
    # Write in binary mode so Windows doesn't expand \n → \r\n.
    out.write_bytes(tiled.encode("utf-8"))
    print(f"  {name}: {out.stat().st_size // MB} MB")

# Default corpus.txt
default = DATA_DIR / "corpus.txt"
if not default.exists():
    import shutil
    shutil.copy2(DATA_DIR / "corpus_100mb.txt", default)
    print("  corpus.txt -> corpus_100mb.txt")
else:
    print(f"  corpus.txt already exists")

print("\nDone. Next steps:")
print("  python python/tokenize_text.py          # Python baseline")
print(f"  dotnet run -c Release --project dotnet/Tokenizer.csproj   # .NET")
