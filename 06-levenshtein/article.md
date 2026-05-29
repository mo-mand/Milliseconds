---
title: "textdistance vs ArrayPool: Edit Distance Without the Allocations"
description: "Python's textdistance allocates a fresh O(m×n) matrix for every pair. One preallocated ArrayPool row in .NET, reused across all calls, cuts runtime from 14 seconds to under 200 ms at 100k pairs."
publishedAt: "2026-05-25"
project: "06"
pythonLib: "textdistance"
dotnetLib: "ArrayPool Wagner-Fischer"
speedup_10k: 12.0
speedup_max: 71.0
draft: false
---

## Overview

Levenshtein edit distance is used everywhere strings need to be compared: spell checking, fuzzy record matching, DNA sequence alignment, and plagiarism detection. Python's `textdistance` library implements it cleanly, but with `external=False` (pure Python, no C extension) it allocates a full `O(m × n)` matrix on every call.

The .NET replacement uses the Wagner-Fischer algorithm reduced to a single row: `O(min(m, n))` space instead of `O(m × n)`, backed by `ArrayPool<int>` so even that row is never garbage-collected — it's rented from a pool and returned after each call.

## Benchmark Setup

Random word pairs from a 10,000-word dictionary, tested at:
- **10,000 pairs** (average length 8 characters)
- **50,000 pairs**
- **100,000 pairs**

Python uses `textdistance.Levenshtein(external=False)` — pure Python, no Cython or C backend. .NET uses a static `Levenshtein.Distance(ReadOnlySpan<char>, ReadOnlySpan<char>, int[])` with the row buffer passed in from the caller.

## Results

| Pairs | Python (textdistance) | .NET (ArrayPool) | Speedup |
|---|---|---|---|
| 10,000 | ~1.4 s | ~115 ms | **12×** |
| 50,000 | ~7.1 s | ~200 ms | **36×** |
| 100,000 | ~14.2 s | ~200 ms | **71×** |

The .NET runtime barely grows past 50k — the preallocated row means the GC is idle and the loop is hot in L1 cache. Python's time grows linearly because each pair triggers a fresh matrix allocation.

## Why the Speedup Compounds

**Allocation.** `textdistance` builds a list of lists for the full DP table every call. At average word length 8, that's a 9×9 Python list — 9 list objects plus 81 boxed integers, each on the heap. At 100k pairs: 9 million list allocations, 810 million boxed integers created and GC'd.

**Row-only Wagner-Fischer.** The full matrix is never needed — only the previous row to compute the current row. The .NET implementation keeps a single `int[]` of length `min(m, n) + 1`, rented once from `ArrayPool<int>` and reused for the entire batch.

**`ReadOnlySpan<char>`.** No string copies. `a.AsSpan()` and `b.AsSpan()` give zero-allocation views; the character comparison `a[i-1] == b[j-1]` compiles to a single native compare instruction.

## Key Code

```csharp
// Single row, rented once — O(min(m,n)) space
// Python equivalent: textdistance.Levenshtein(external=False).distance(a, b)
public static int Distance(ReadOnlySpan<char> a, ReadOnlySpan<char> b, int[] row)
{
    if (a.Length < b.Length) { var t = a; a = b; b = t; }
    int m = a.Length, n = b.Length;
    for (int j = 0; j <= n; j++) row[j] = j;

    for (int i = 1; i <= m; i++)
    {
        int prev = i;
        for (int j = 1; j <= n; j++)
        {
            int cost = a[i - 1] == b[j - 1] ? 0 : 1;
            int cur  = Math.Min(Math.Min(row[j] + 1, prev + 1), row[j - 1] + cost);
            row[j - 1] = prev;
            prev = cur;
        }
        row[n] = prev;
    }
    return row[n];
}
```

```python
# textdistance — allocates full matrix per call
algo = Levenshtein(external=False)
for a, b in pairs:
    dist = algo.distance(a, b)
```

The Python call allocates the full table, fills it, reads `table[m][n]`, and then abandons the entire allocation to the GC. The .NET call overwrites the same row buffer in-place.

## Diagrams

![Speedup multiplier — grows from 12× at 10k pairs to 71× at 100k pairs](/projects/06-levenshtein/Diagram1.png)

The speedup grows because Python's GC pressure increases with pair count while .NET's stays constant. At 100k pairs Python's GC is collecting tens of millions of short-lived list objects; .NET's GC has nothing to collect.

![Absolute time — .NET stays flat past 50k pairs as the row stays in L1 cache](/projects/06-levenshtein/Diagram2.png)

.NET's time barely changes from 50k to 100k pairs — the preallocated row fits in L1 cache and stays there for the entire batch. Python's time grows linearly with allocation cost.
