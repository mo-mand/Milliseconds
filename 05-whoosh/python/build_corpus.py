"""
Build JSONL document corpora from NLTK's Reuters and Brown corpora.

Outputs (in data/):
    docs_10k.jsonl    10 000 documents
    docs_50k.jsonl    50 000 documents
    docs_100k.jsonl  100 000 documents

Each line: {"id": "...", "title": "...", "body": "..."}

Usage:
    python build_corpus.py
"""

import json
import nltk
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

for pkg in ("reuters", "brown", "gutenberg", "punkt", "punkt_tab"):
    nltk.download(pkg, quiet=True)

from nltk.corpus import reuters, brown, gutenberg

# ---- Collect base documents -------------------------------------------------
docs = []

# Reuters: 11 000 news articles — each is a real document with a clear title.
for fid in reuters.fileids():
    raw = reuters.raw(fid).strip()
    lines = [l.strip() for l in raw.splitlines() if l.strip()]
    title = lines[0][:120] if lines else fid
    body  = " ".join(lines[1:]) if len(lines) > 1 else lines[0] if lines else ""
    if len(body) > 50:
        docs.append({"id": f"reuters_{fid}", "title": title, "body": body})

# Brown corpus: 500 genre sections, each split into ~20-word chunks.
for cat in brown.categories():
    words = brown.words(categories=cat)
    chunk_size = 200
    for i in range(0, len(words), chunk_size):
        chunk = " ".join(words[i:i+chunk_size])
        if len(chunk) > 50:
            docs.append({"id": f"brown_{cat}_{i}", "title": chunk[:80], "body": chunk})

# Gutenberg: classic novels split into paragraphs.
for fid in gutenberg.fileids():
    paragraphs = gutenberg.raw(fid).split("\n\n")
    for j, para in enumerate(paragraphs):
        para = para.strip()
        if len(para) > 100:
            docs.append({"id": f"gut_{fid}_{j}", "title": para[:80], "body": para})

print(f"Base documents collected: {len(docs):,}")

# ---- Write corpora ----------------------------------------------------------
TARGETS = {"docs_10k.jsonl": 10_000, "docs_50k.jsonl": 50_000, "docs_100k.jsonl": 100_000}

for name, n in TARGETS.items():
    out = DATA_DIR / name
    if out.exists():
        print(f"  {name} already exists")
        continue
    # Tile docs to reach target count, giving each a unique id.
    with open(out, "w", encoding="utf-8") as f:
        written = 0
        cycle = 0
        while written < n:
            for doc in docs:
                if written >= n:
                    break
                tiled = {
                    "id":    f"{doc['id']}_c{cycle}",
                    "title": doc["title"],
                    "body":  doc["body"],
                }
                f.write(json.dumps(tiled) + "\n")
                written += 1
            cycle += 1
    size_kb = out.stat().st_size // 1024
    print(f"  {name}: {written:,} docs  ({size_kb:,} KB)")

print("\nDone.")
