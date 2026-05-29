"""
Project 1: Aurora — Download real WikiText-103 + run GPT-2 → save real logits.

This is the "real data" path. The output binary files are then loaded
identically by both the Python and .NET benchmarks for an apples-to-apples
comparison on production NLP data.

Requires:
    pip install torch transformers datasets numpy

Output:
    data/wikitext_logits.bin   — float32 [N_tokens × 50,257]
    data/wikitext_targets.bin  — int32   [N_tokens]
    data/wikitext_meta.json    — {"n_tokens": N, "vocab": 50257, "model": "gpt2"}

Usage:
    python prepare_real_logits.py                  # 50K tokens (~12 GB RAM)
    python prepare_real_logits.py --tokens 10000   # smaller for laptops
"""

import argparse
import json
import sys
from pathlib import Path


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--tokens", type=int, default=50_000,
                   help="How many tokens of WikiText-103 to evaluate")
    p.add_argument("--model",  type=str, default="gpt2",
                   help="HF model id (gpt2, gpt2-medium, etc.)")
    p.add_argument("--output", type=str, default="../data",
                   help="Output directory")
    args = p.parse_args()

    try:
        import torch
        import numpy as np
        from transformers import GPT2LMHeadModel, GPT2TokenizerFast
        from datasets import load_dataset
    except ImportError as e:
        sys.exit(f"Missing dependency: {e}\n"
                 "Install with: pip install torch transformers datasets numpy")

    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Loading {args.model} model + tokenizer...")
    tokenizer = GPT2TokenizerFast.from_pretrained(args.model)
    model = GPT2LMHeadModel.from_pretrained(args.model)
    model.eval()
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model.to(device)
    print(f"  Device: {device}")
    print(f"  Vocab:  {model.config.vocab_size:,}")

    print("Downloading WikiText-103-raw-v1 validation split...")
    ds = load_dataset("wikitext", "wikitext-103-raw-v1", split="validation")
    text = "\n\n".join(t for t in ds["text"] if t.strip())
    print(f"  Text: {len(text):,} chars")

    print("Tokenizing...")
    ids = tokenizer.encode(text)
    ids = ids[:args.tokens + 1]  # +1 because we predict next token
    print(f"  Tokens: {len(ids):,}")

    # Run model in chunks of 1024 (GPT-2 context length)
    print(f"Running {args.model} forward pass...")
    chunk_size = 1024
    all_logits = []
    all_targets = []

    with torch.no_grad():
        for start in range(0, len(ids) - 1, chunk_size):
            end = min(start + chunk_size, len(ids) - 1)
            input_ids = torch.tensor([ids[start:end]], device=device)
            target_ids = ids[start + 1:end + 1]
            out = model(input_ids)
            # out.logits: [1, seq_len, vocab]  → save as float32
            all_logits.append(out.logits[0].cpu().float().numpy())
            all_targets.extend(target_ids)
            print(f"  processed {end:,}/{len(ids) - 1:,} tokens", end="\r")
    print()

    logits  = np.concatenate(all_logits, axis=0).astype(np.float32)
    targets = np.array(all_targets, dtype=np.int32)
    print(f"  logits  shape: {logits.shape}, dtype={logits.dtype}, size={logits.nbytes / 1_048_576:.1f} MB")
    print(f"  targets shape: {targets.shape}")

    # Save as raw binary so .NET can load with simple File.OpenRead
    logits.tofile(out_dir / "wikitext_logits.bin")
    targets.tofile(out_dir / "wikitext_targets.bin")
    with open(out_dir / "wikitext_meta.json", "w") as f:
        json.dump({
            "n_tokens": int(targets.shape[0]),
            "vocab":    int(logits.shape[1]),
            "model":    args.model,
            "dataset":  "wikitext-103-raw-v1 (validation)",
        }, f, indent=2)

    print(f"\nSaved to {out_dir.resolve()}")
    print("Now run benchmarks:")
    print("  python perplexity_real.py")
    print(f"  cd ../dotnet/PerplexityBench && dotnet run -c Release -- "
          f"--real {(out_dir / 'wikitext_logits.bin').resolve()} "
          f"{(out_dir / 'wikitext_targets.bin').resolve()}")


if __name__ == "__main__":
    main()
