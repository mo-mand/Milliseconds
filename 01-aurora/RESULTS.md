# Project 1: Aurora — Measured Results

Real measurements from a single Windows 11 machine, .NET 10.0.5, Python 3.13 + NumPy.
These are the numbers we observed; your hardware will produce different absolute values
but the *ratios* between implementations should be similar on any AVX2 CPU.

## Workload A — GPT-2 vocab (50,257) × 20,000 tokens

| Implementation                       | Time    | Notes                                |
|--------------------------------------|---------|--------------------------------------|
| .NET 10  LogSoftmax fused (best)     | **0.94 s**  | TensorPrimitives Max/Subtract/Exp/Sum chained |
| Python   NumPy LogSumExp (best)      | **0.99 s**  | per-row loop, BLAS-backed reduction |
| Python   NumPy pure                  | 1.13 s  | the most-common idiomatic Python    |
| .NET 10  TensorPrimitives.SoftMax    | 1.69 s  | per-row, default .NET path          |
| Python   NumPy fully vectorized      | 2.38 s  | suffers from intermediate allocation |
| Python   scipy.special.softmax       | 3.32 s  | same problem, plus ufunc overhead   |
| .NET 10  Fused Span<T> (no SIMD)     | 3.65 s  | best non-SIMD .NET                  |
| .NET 10  Scalar C# (naive)           | 3.87 s  | what unoptimized .NET looks like    |

**Verdict at GPT-2 scale:** essentially tied. .NET's fused path edges out NumPy by ~5%.

## Workload B — Llama 3 vocab (128,256) × 5,000 tokens

| Implementation                     | Time     | Speedup vs best Python |
|------------------------------------|----------|-----------------------|
| .NET 10  TensorPrimitives.SoftMax  | **4.17 s** | **1.53x faster**     |
| .NET 10  LogSoftmax fused          | 4.33 s   | 1.48x                 |
| Python   NumPy LogSumExp           | **6.40 s** | baseline (best Python) |
| Python   NumPy pure                | 7.24 s   | -                     |
| Python   NumPy fully vectorized    | 8.41 s   | -                     |
| Python   scipy.special.softmax     | 10.45 s  | -                     |
| .NET 10  Scalar C# (naive)         | 10.89 s  | -                     |

**Verdict at Llama-3 scale:** .NET wins by **1.53x**. The larger the vocab, the bigger
the gap — because .NET reuses a single SIMD buffer while NumPy's allocation cost
grows with vocab size.

## Why the gap widens with vocab size

- **NumPy** allocates intermediate arrays for `shifted = x - max`, then `np.exp(shifted)`,
  then sum. At 50K vocab each is 200KB; at 128K vocab each is 512KB. Cache pressure
  grows non-linearly past L2 cache.
- **.NET TensorPrimitives** uses a single reusable scratch buffer; the SIMD loop
  stays in L1/L2 cache regardless of total array size.

## Extrapolation to real corpus-scale evaluations

Linear scaling in token count, measured per-token rates from above:

| Real workload                                     | Python (best) | .NET 10 (best) | Saves     |
|---------------------------------------------------|---------------|----------------|-----------|
| WikiText-103 valid set, GPT-2 (280K × 50K)        | ~14 s         | ~13 s          | tied      |
| WikiText-103 valid set, Llama-3 (280K × 128K)     | ~6 min        | ~4 min         | ~2 min    |
| 100M-token eval, Llama-3 vocab                    | ~36 hr        | ~23 hr         | ~13 hr    |
| 1B-token eval, Llama-3 vocab                      | ~15 days      | ~9.6 days      | **~5 days** |
| 10B-token eval, Llama-3 vocab (Common Crawl scale)| ~148 days     | ~96 days       | **~52 days** |

These are the kind of savings that matter. Eval pipelines, batch inference,
re-indexing — anything CPU-bound at scale.

## What this benchmark does NOT measure

- **GPU inference** — not the bottleneck on GPU; this benchmark is for CPU pipelines
- **Single-vector latency** — at ~1 ms/token both are fast enough; this is about throughput
- **End-to-end LLM serving** — that's dominated by attention, not softmax
- **Model accuracy** — we use synthetic logits to isolate the post-processing cost

## How to reproduce

```bash
# .NET (synthetic, GPT-2 scale)
cd dotnet/PerplexityBench
dotnet run -c Release -- --tokens 20000

# .NET (synthetic, Llama-3 scale)
dotnet run -c Release -- --vocab 128256 --tokens 5000

# Python equivalents
cd ../../python
python perplexity_synthetic.py --tokens 20000
python perplexity_synthetic.py --vocab 128256 --tokens 5000

# Real WikiText-103 + GPT-2 (requires pip install torch transformers datasets)
python prepare_real_logits.py --tokens 50000
python perplexity_real.py
cd ../dotnet/PerplexityBench && dotnet run -c Release -- --real ../../data/wikitext_logits.bin ../../data/wikitext_targets.bin
```

## Source

Pipeline matches the Hugging Face `evaluate` library's perplexity metric:
https://github.com/huggingface/evaluate/blob/main/metrics/perplexity/perplexity.py

Numerically stable softmax (subtract max before exp) is the standard recipe;
log-domain cross-entropy avoids materializing the full probability distribution.
