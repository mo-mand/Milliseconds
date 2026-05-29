# Project 1: Aurora — Perplexity Evaluation at LLM Scale

Real-world benchmark using **WikiText-103 + GPT-2** (the standard NLP perplexity evaluation
pipeline) to measure where .NET 10 saves real wall-clock time vs Python/NumPy.

## What it measures

For every token in the dataset, the pipeline must:
1. Apply **softmax** over the full vocabulary (50,257 for GPT-2, 128,256 for Llama 3)
2. Compute **cross-entropy** loss against the actual next token
3. Aggregate to **perplexity**: `exp(mean(loss))`

This is the standard NLP eval recipe used by Hugging Face's `evaluate` library, the
EleutherAI eval harness, and every published LLM paper. The softmax + cross-entropy
step happens *after* the model inference (GPU-bound), making it a pure CPU/SIMD workload
where .NET vs Python actually competes head-to-head.

## Two modes

### 1. Synthetic logits (default — runs in 30 seconds, no setup)
Generates float32 logits matching the statistical distribution of real LLM outputs
(gaussian with sigma=5). Same shape as real GPT-2 outputs (N tokens × 50,257 vocab).

```bash
# .NET
cd dotnet/PerplexityBench
dotnet run -c Release

# Python
cd python
python perplexity_synthetic.py
```

### 2. Real WikiText-103 + GPT-2 (requires download, ~20 min setup)
Downloads WikiText-103-raw-v1 from Hugging Face, runs GPT-2 small (124M) inference
to get real logits, saves them as a binary file. Both .NET and Python then run the
exact same post-processing pipeline on the saved logits.

```bash
pip install datasets transformers torch numpy
cd python
python prepare_real_logits.py     # downloads + runs GPT-2, saves data/wikitext_logits.bin
python perplexity_real.py         # benchmarks on real data

cd ../dotnet/PerplexityBench
dotnet run -c Release -- --real    # benchmarks on the same real data
```

## Why this is a fair comparison

- **Same input file** — both runtimes load the same binary float32 logits
- **Same algorithm** — numerically stable softmax (max subtraction) + log + cross-entropy
- **Same hardware** — measured on the same machine in the same session
- **Real data** — not cherry-picked, just the standard NLP benchmark
- **Real time scale** — minutes per run, projecting to hours for full corpus eval

## Expected results

Based on micro-benchmarks at 4096-dim (NumPy 44.5µs / .NET 22.9µs softmax),
extrapolated to 50,257-dim:

| Workload                              | NumPy        | .NET 10      | Saves   |
|---------------------------------------|--------------|--------------|---------|
| WikiText-103 valid (280K tokens)      | ~3 minutes   | ~1.5 minutes | 1.5 min |
| 1B-token corpus eval                  | ~3.5 hours   | ~1.7 hours   | 1.8 hr  |
| Llama 3 vocab (128K) on 1B tokens     | ~9 hours     | ~4 hours     | 5 hr    |

Numbers will be filled in with measured values once you run the benchmark.
