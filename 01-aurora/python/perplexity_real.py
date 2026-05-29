"""
Project 1: Aurora — Perplexity benchmark on REAL GPT-2 logits.

Loads the binary files produced by prepare_real_logits.py and benchmarks the
post-processing pipeline (softmax → cross-entropy → perplexity).

Run prepare_real_logits.py first.
"""

import json
import time
from pathlib import Path

import numpy as np

DATA_DIR = Path(__file__).parent.parent / "data"


def perplexity_pure_numpy(logits: np.ndarray, targets: np.ndarray) -> float:
    sum_nll = 0.0
    n = len(targets)
    for t in range(n):
        row = logits[t]
        max_val = row.max()
        shifted = row - max_val
        exp = np.exp(shifted)
        probs = exp / exp.sum()
        sum_nll += -np.log(max(probs[targets[t]], 1e-30))
    return float(np.exp(sum_nll / n))


def perplexity_vectorized(logits: np.ndarray, targets: np.ndarray) -> float:
    """Best-case NumPy: full vectorization across the token axis."""
    max_per_row = logits.max(axis=1, keepdims=True)
    shifted     = logits - max_per_row
    log_sum_exp = np.log(np.exp(shifted).sum(axis=1))
    target_logits = shifted[np.arange(len(targets)), targets]
    nll = -(target_logits - log_sum_exp)
    return float(np.exp(nll.mean()))


def time_it(label: str, fn) -> tuple[float, float]:
    t0 = time.perf_counter()
    ppl = fn()
    elapsed = time.perf_counter() - t0
    print(f"  {label:<40} {elapsed:>7.2f} s   →  ppl={ppl:8.2f}")
    return elapsed, ppl


def main():
    meta_path = DATA_DIR / "wikitext_meta.json"
    if not meta_path.exists():
        raise SystemExit(f"Run prepare_real_logits.py first — {meta_path} not found")

    meta = json.loads(meta_path.read_text())
    print(f"=== Real GPT-2 logits on WikiText-103 ===")
    print(f"  Model:    {meta['model']}")
    print(f"  Dataset:  {meta['dataset']}")
    print(f"  Tokens:   {meta['n_tokens']:,}")
    print(f"  Vocab:    {meta['vocab']:,}")

    logits  = np.fromfile(DATA_DIR / "wikitext_logits.bin",  dtype=np.float32)
    targets = np.fromfile(DATA_DIR / "wikitext_targets.bin", dtype=np.int32)
    logits = logits.reshape(meta["n_tokens"], meta["vocab"])
    print(f"  Loaded {logits.nbytes / 1_048_576:,.0f} MB of logits\n")

    print("=== Pipeline: softmax → log(p[target]) → mean → exp(NLL) ===\n")

    # warm-up
    perplexity_vectorized(logits[:100], targets[:100])

    time_it("NumPy pure (per-row loop)               ", lambda: perplexity_pure_numpy(logits, targets))
    time_it("NumPy vectorized (best Python possible) ", lambda: perplexity_vectorized(logits, targets))

    print(f"\nReference perplexity for GPT-2 on WikiText-103: ~30")


if __name__ == "__main__":
    main()
