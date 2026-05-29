"""
Generate word-pair datasets from NLTK's English word list.

Outputs (in data/):
    pairs_100k.tsv    100 000 pairs
    pairs_500k.tsv    500 000 pairs
    pairs_1m.tsv    1 000 000 pairs

Each line: "word1\tword2"
Pairs are drawn randomly so they cover a realistic mix of edit distances.

Usage:
    python build_pairs.py
"""

import random
import nltk
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

nltk.download("words", quiet=True)
from nltk.corpus import words as nltk_words

# Use words between 3 and 15 characters — realistic for spell-check / fuzzy-search.
word_list = [w.lower() for w in nltk_words.words("en")
             if 3 <= len(w) <= 15 and w.isalpha()]
word_list = list(set(word_list))   # deduplicate
random.seed(42)
random.shuffle(word_list)
print(f"Vocabulary size: {len(word_list):,} words")

TARGETS = {
    "pairs_100k.tsv":   100_000,
    "pairs_500k.tsv":   500_000,
    "pairs_1m.tsv":   1_000_000,
}

for name, n in TARGETS.items():
    out = DATA_DIR / name
    if out.exists():
        print(f"  {name} already exists")
        continue
    N = len(word_list)
    rng = random.Random(42)
    with open(out, "w", encoding="utf-8") as f:
        for _ in range(n):
            a = word_list[rng.randrange(N)]
            b = word_list[rng.randrange(N)]
            f.write(f"{a}\t{b}\n")
    print(f"  {name}: {n:,} pairs  ({out.stat().st_size // 1024:,} KB)")

print("\nDone.")
