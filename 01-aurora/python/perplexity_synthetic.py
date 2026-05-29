"""
Project 1: Aurora — Perplexity benchmark on synthetic logits.

Mirrors the .NET PerplexityBench exactly: same data shape, same algorithm,
same numerical stability strategy. Only the language differs.

Usage:
    python perplexity_synthetic.py                       # GPT-2 vocab (50,257), 100K tokens
    python perplexity_synthetic.py --vocab 128256        # Llama-3 vocab
    python perplexity_synthetic.py --tokens 1000000      # 1M tokens
"""

import argparse
import time
import numpy as np
from scipy.special import softmax as scipy_softmax  # type: ignore  (optional)


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--vocab",  type=int, default=50257,   help="Vocabulary size (default: GPT-2)")
    p.add_argument("--tokens", type=int, default=100_000, help="Number of tokens to evaluate")
    p.add_argument("--seed",   type=int, default=42)
    return p.parse_args()


def perplexity_pure_numpy(logits: np.ndarray, targets: np.ndarray) -> float:
    """Standard NumPy implementation — what most Python code looks like."""
    sum_nll = 0.0
    n = len(targets)
    for t in range(n):
        row = logits[t]
        # numerically stable softmax
        max_val = row.max()
        shifted = row - max_val
        exp = np.exp(shifted)
        probs = exp / exp.sum()
        sum_nll += -np.log(max(probs[targets[t]], 1e-30))
    return float(np.exp(sum_nll / n))


def perplexity_logsumexp(logits: np.ndarray, targets: np.ndarray) -> float:
    """LogSumExp trick — avoids materializing softmax probabilities."""
    sum_nll = 0.0
    n = len(targets)
    for t in range(n):
        row = logits[t]
        max_val = row.max()
        shifted = row - max_val
        log_sum_exp = np.log(np.exp(shifted).sum())
        log_p_target = shifted[targets[t]] - log_sum_exp
        sum_nll += -log_p_target
    return float(np.exp(sum_nll / n))


def perplexity_vectorized(logits: np.ndarray, targets: np.ndarray) -> float:
    """Fully vectorized — what the best NumPy programmer writes.
       This is the version hard to beat: NumPy only crosses the Python/C boundary once."""
    max_per_row = logits.max(axis=1, keepdims=True)
    shifted     = logits - max_per_row
    log_sum_exp = np.log(np.exp(shifted).sum(axis=1))
    target_logits = shifted[np.arange(len(targets)), targets]
    nll = -(target_logits - log_sum_exp)
    return float(np.exp(nll.mean()))


def time_it(label: str, fn) -> tuple[float, float]:
    # warm-up
    t0 = time.perf_counter()
    ppl = fn()
    elapsed = time.perf_counter() - t0
    print(f"  {label:<40} {elapsed:>7.2f} s   ->  ppl={ppl:8.2f}")
    return elapsed, ppl


def main():
    args = parse_args()

    print(f"=== Generating synthetic logits ===")
    print(f"  Vocab size:  {args.vocab:,}")
    print(f"  Tokens:      {args.tokens:,}")
    print(f"  Memory:      {args.tokens * args.vocab * 4 / 1_048_576:,.0f} MB")
    print(f"  Distribution: gaussian sigma=5 (matches real LLM output stats)\n")

    rng = np.random.default_rng(args.seed)
    t0 = time.perf_counter()
    logits  = rng.normal(0.0, 5.0, size=(args.tokens, args.vocab)).astype(np.float32)
    targets = rng.integers(0, args.vocab, size=args.tokens).astype(np.int32)
    print(f"Generated in {time.perf_counter() - t0:.1f}s\n")

    print("=== Pipeline: softmax -> log(p[target]) -> mean -> exp(NLL) ===\n")

    # warm-up: small slice
    perplexity_vectorized(logits[:100], targets[:100])

    time_it("NumPy pure (per-row loop)               ", lambda: perplexity_pure_numpy(logits, targets))
    time_it("NumPy LogSumExp (per-row loop)          ", lambda: perplexity_logsumexp(logits, targets))
    time_it("NumPy vectorized (best Python possible) ", lambda: perplexity_vectorized(logits, targets))

    try:
        time_it("scipy.special.softmax + index           ",
                lambda: float(np.exp(-np.log(scipy_softmax(logits, axis=1)
                                             [np.arange(len(targets)), targets]
                                             .clip(1e-30, 1.0)).mean())))
    except Exception as e:
        print(f"  (scipy benchmark skipped: {e})")


if __name__ == "__main__":
    main()
