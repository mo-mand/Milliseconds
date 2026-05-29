"""
Tokenizer — pure Python, NLTK (zero C extensions).

Runs sentence + word tokenization on a plain-text file using NLTK's
standard Punkt sentence splitter and word_tokenize.

Usage:
    python tokenize_text.py [path/to/corpus.txt] [--json]
"""

import sys
import json
import time
from pathlib import Path

try:
    import nltk
except ImportError:
    sys.exit("nltk not installed. Run: pip install nltk")

# Ensure required NLTK data is present.
for pkg in ("punkt", "punkt_tab"):
    try:
        nltk.data.find(f"tokenizers/{pkg}")
    except LookupError:
        nltk.download(pkg, quiet=True)

JSON_MODE = "--json" in sys.argv
path_args = [a for a in sys.argv[1:] if not a.startswith("--")]

text_path = Path(path_args[0]) if path_args else \
            Path(__file__).parent.parent / "data" / "corpus.txt"

if not text_path.exists():
    sys.exit(f"File not found: {text_path}\nRun: python download_data.py")

def log(msg):
    if not JSON_MODE:
        print(msg, flush=True)

log(f"Reading: {text_path}")
t0 = time.perf_counter()
text = text_path.read_text(encoding="utf-8")
load_ms = (time.perf_counter() - t0) * 1000
log(f"Size: {len(text):,} chars  (loaded in {load_ms:.0f} ms)")

log("Tokenizing sentences ...")
t1 = time.perf_counter()

sentences = nltk.sent_tokenize(text)
sent_count = len(sentences)

word_count = 0
for sent in sentences:
    word_count += len(nltk.word_tokenize(sent))

compute_ms = (time.perf_counter() - t1) * 1000

if JSON_MODE:
    print(json.dumps({
        "chars":      len(text),
        "sentences":  sent_count,
        "words":      word_count,
        "load_ms":    round(load_ms, 1),
        "compute_ms": round(compute_ms, 1),
    }))
else:
    print(f"\nSentences : {sent_count:,}")
    print(f"Words     : {word_count:,}")
    print(f"Elapsed   : {compute_ms:.1f} ms")
    print(f"Throughput: {len(text) / (compute_ms / 1000) / 1_000_000:.4f} MB/s")
