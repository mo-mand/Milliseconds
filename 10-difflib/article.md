---
title: "Difflib vs DP LCS: 21× Speedup Rewiring Python's Diff Engine"
description: "Python's difflib uses Ratcliff/Obershelp with per-call matrix allocation. We replaced it with a preallocated DP LCS buffer in .NET and eliminated GC pressure entirely."
publishedAt: "2026-05-27"
project: "10"
pythonLib: "difflib"
dotnetLib: "Custom DP LCS"
speedup_10k: 5.6
speedup_max: 21.3
draft: false
---

## Overview

Python's `difflib.SequenceMatcher` is one of the most used modules in the standard library — code review tools, merge conflict resolution, and fuzzy search all lean on it. The algorithm underneath is Ratcliff/Obershelp, which allocates a fresh matrix on every call. At 10,000 pairs that's manageable; at 100,000 pairs the garbage collector becomes the bottleneck.

The .NET replacement uses classic DP LCS (Longest Common Subsequence) on integer-encoded sequences. The key trick: one preallocated `int[]` buffer reused across every pair, so the GC sees zero pressure after warmup.

## Benchmark Setup

Test data is pairs of integer sequences (vocabulary size 9,000), each 80–200 elements long, with approximately 15% deletions, 10% substitutions, and 10% insertions per pair. Integer encoding keeps I/O negligible and isolates the diff algorithm itself.

Dataset sizes tested: **10,000 / 50,000 / 100,000 pairs**.

## Results

| Dataset | Python (difflib) | .NET (DP LCS) | Speedup |
|---------|-----------------|---------------|---------|
| 10,000  | ~1.3 s          | ~230 ms       | **5.6×**  |
| 50,000  | ~6.5 s          | ~305 ms       | **21.3×** |
| 100,000 | ~13 s           | ~960 ms       | **13.5×** |

The 50k peak at 21× reflects .NET's GC advantage most clearly: Python's allocator buckles under the sustained object churn while .NET hums along with a single live buffer.

## Diagrams

![Speedup multiplier by dataset size — .NET peaks at 21× at 50k pairs](/projects/10-difflib/Diagram1.png)

Diagram 1 shows the speedup multiplier across the three dataset sizes. The 10k result (5.6×) reflects Python's overhead even at moderate scale. The jump to 21× at 50k is where GC pressure in Python compresses throughput — the GC is spending real time collecting the matrix objects. At 100k the speedup drops back to 13.5×, because .NET's own JIT warmup and memory pressure become measurable at this scale.

![Absolute execution time in milliseconds — Python scales linearly, .NET stays nearly flat](/projects/10-difflib/Diagram2.png)

Diagram 2 shows absolute execution time. Python's line rises steeply and linearly — each pair costs roughly the same, plus a growing GC tax. The .NET line is almost flat from 10k to 50k (the preallocated buffer means no marginal allocation cost per pair), then rises modestly to 100k as cache pressure builds.

## Why .NET Wins

Two factors compound each other:

**1. Zero per-pair allocation.** The DP buffer is preallocated once at startup:
`int[] dpBuf = new int[MaxLen * MaxLen]` with `MaxLen = 210`. Every diff reuses this flat array via index arithmetic `dp[i * stride + j]`, so the GC has nothing to collect between pairs.

**2. Flat integer arrays outperform Python list-of-lists.** Python's 2D matrix is a list of list objects — each row is a separate heap allocation with its own reference count. The .NET flat array is a single contiguous block, which is cache-friendly and requires no pointer indirection.

## Key Code

```csharp
// .NET — single buffer, reused across all pairs
int[] dpBuf = new int[MaxLen * MaxLen];
foreach (var (a, b) in pairs)
{
    int ins = 0, dels = 0, unch = 0;
    DiffCounts(a, b, dpBuf, MaxLen, ref ins, ref dels, ref unch);
    checksum += unch;
}

static void DiffCounts(int[] a, int[] b, int[] dp, int stride,
                        ref int ins, ref int dels, ref int unch)
{
    int n = a.Length, m = b.Length;
    for (int i = 1; i <= n; i++)
        for (int j = 1; j <= m; j++)
            dp[i * stride + j] = a[i-1] == b[j-1]
                ? dp[(i-1) * stride + (j-1)] + 1
                : Math.Max(dp[(i-1) * stride + j], dp[i * stride + (j-1)]);
    unch = dp[n * stride + m];
    ins  = m - unch;
    dels = n - unch;
}
```

```python
# Python — allocates new internal state per call
matcher = SequenceMatcher(None, a, b, autojunk=False)
blocks  = matcher.get_matching_blocks()
unch    = sum(t.size for t in blocks)
```
