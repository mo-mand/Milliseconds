"""
Build Markdown document datasets from NLTK corpora.

Each "document" is one paragraph rendered as Markdown with
inline formatting (bold, italic, code spans, headers, lists).

Outputs (in data/):
    docs_10k.txt    10 000 docs, one per line
    docs_50k.txt    50 000 docs
    docs_100k.txt  100 000 docs

Usage:
    python build_corpus.py
"""

import random
import re
import nltk
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

for corpus in ("gutenberg", "brown", "reuters"):
    nltk.download(corpus, quiet=True)

from nltk.corpus import gutenberg, brown, reuters

def get_sentences():
    sents = []
    for fid in gutenberg.fileids():
        sents.extend([" ".join(s) for s in gutenberg.sents(fid)])
    for fid in brown.fileids():
        sents.extend([" ".join(s) for s in brown.sents(fid)])
    for fid in reuters.fileids():
        sents.extend([" ".join(s) for s in reuters.sents(fid)])
    return [s for s in sents if 10 <= len(s) <= 300]

print("Loading NLTK corpora ...")
sentences = get_sentences()
print(f"  {len(sentences):,} sentences loaded")

rng = random.Random(42)
rng.shuffle(sentences)

HEADERS = ["# {t}", "## {t}", "### {t}"]
EMPH    = ["**{w}**", "*{w}*", "`{w}`"]

def make_doc(idx: int) -> str:
    sent = sentences[idx % len(sentences)]
    words = sent.split()
    if not words:
        return "# empty"

    # random header
    title = " ".join(words[:min(6, len(words))])
    title = re.sub(r"[^\w\s]", "", title).strip() or "Document"
    header = rng.choice(HEADERS).format(t=title)

    # body: sprinkle inline formatting
    body_words = list(words)
    for i in range(0, len(body_words), rng.randint(5, 9)):
        if i < len(body_words):
            body_words[i] = rng.choice(EMPH).format(w=body_words[i].strip(".,;:!?") or "word")
    body = " ".join(body_words)

    # optional bullet list
    list_items = ""
    if rng.random() < 0.4:
        items = [sentences[(idx + j + 1) % len(sentences)].split()[:5] for j in range(3)]
        list_items = " ".join(f"- {' '.join(it)}" for it in items if it)

    parts = [header, body]
    if list_items:
        parts.append(list_items)

    # collapse to single line (one doc per line in TSV)
    return "  ".join(parts)

TARGETS = {
    "docs_10k.txt":  10_000,
    "docs_50k.txt":  50_000,
    "docs_100k.txt": 100_000,
}

for name, n in TARGETS.items():
    out = DATA_DIR / name
    if out.exists():
        print(f"  {name} already exists — skipping")
        continue
    lines = [make_doc(i) for i in range(n)]
    out.write_bytes(("\n".join(lines) + "\n").encode("utf-8"))
    print(f"  {name}: {n:,} docs  ({out.stat().st_size // 1024:,} KB)")

print("\nDone.")
