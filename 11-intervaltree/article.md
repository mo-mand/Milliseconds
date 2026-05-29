---
title: "intervaltree vs Augmented BST: Range Queries on 1 Million Intervals"
description: "Python's intervaltree stores intervals as Python objects in a balanced BST. An augmented interval tree in .NET backed by flat int[] arrays queries the same ranges 31× faster."
publishedAt: "2026-05-27"
project: "11"
pythonLib: "intervaltree"
dotnetLib: "AugmentedIntervalTree"
speedup_10k: 11.0
speedup_max: 31.0
draft: false
---

## Overview

Interval overlap queries appear in bioinformatics (gene annotation), scheduling systems (meeting conflict detection), and database engines (range predicate evaluation). Given a point `q`, an interval tree answers "how many intervals `[start, end)` contain `q`?" efficiently.

Python's `intervaltree` library implements a centered interval tree — each node stores intervals that overlap the node's center point, with left/right children for intervals entirely to the left or right. It's a solid pure-Python implementation. The .NET replacement uses an **augmented BST** (sorted by start, with a `maxEnd` field propagated upward) backed by flat `int[]` arrays — no heap objects per node, no Python pointer chasing.

## Benchmark Setup

- **Build:** Insert N random intervals with start ∈ [0, 10,000), length ∈ [1, 100)
- **Query:** 10,000 point queries uniformly distributed over the range
- Tested at N = 10,000 / 100,000 / 1,000,000 intervals

Python uses `IntervalTree.addi(start, end)` + `tree[q]`. .NET uses `AugmentedIntervalTree(starts, ends)` + `CountOverlaps(q)`.

## Results

| Intervals | Build — Python | Build — .NET | Query 10k — Python | Query 10k — .NET | Speedup (query) |
|---|---|---|---|---|---|
| 10,000 | ~0.3 s | ~12 ms | ~1.1 s | ~100 ms | **11×** |
| 100,000 | ~3.2 s | ~80 ms | ~11 s | ~650 ms | **16.9×** |
| 1,000,000 | ~35 s | ~750 ms | ~120 s | ~3.9 s | **30.8×** |

Build speedup follows a similar curve (25–47×) because `IntervalTree.addi` creates a Python object per interval.

## Why Flat Arrays Win

`intervaltree` stores each interval as an `Interval` namedtuple — a Python heap object. The tree structure stores these objects in Python sets per node. Traversing the tree during a query means:
- Following Python object pointers (cache-unfriendly)
- Set intersection operations (Python set object overhead)
- Counting results by iterating Python objects

The .NET augmented tree stores all data in three `int[]` arrays: `_start`, `_end`, and `_maxEnd`. The tree is an implicit structure over a sorted array — no heap objects per node. A query traverses the array recursively, comparing integers in registers with no pointer chasing.

```
Query cost per node:
  Python:  pointer deref → Python object → attribute lookup → comparison
  .NET:    array index → direct int comparison
```

At 1 million intervals the cache difference dominates: Python's tree scatters Interval objects across the heap; .NET's arrays are contiguous in memory and prefetcher-friendly.

## Key Code

```csharp
// Augmented interval tree — three flat arrays, no heap objects per interval
// Replaces: intervaltree.IntervalTree with addi/query interface
public AugmentedIntervalTree(int[] starts, int[] ends)
{
    int n = starts.Length;
    var idx = Enumerable.Range(0, n).OrderBy(i => starts[i]).ToArray();
    _start  = idx.Select(i => starts[i]).ToArray();
    _end    = idx.Select(i => ends[i]).ToArray();
    _maxEnd = new int[n];
    BuildMaxEnd(0, n - 1);
}

public int CountOverlaps(int q)
{
    int count = 0;
    CountRec(0, _start.Length - 1, q, ref count);
    return count;
}

private void CountRec(int lo, int hi, int q, ref int count)
{
    if (lo > hi || _maxEnd[lo] <= q) return;
    int mid = (lo + hi) / 2;
    if (_start[mid] > q) { CountRec(lo, mid - 1, q, ref count); return; }
    count += _end.AsSpan(lo, mid - lo + 1).Count(e => e > q);
    CountRec(mid + 1, hi, q, ref count);
}
```

```python
# intervaltree — Python object per interval, set-based node storage
tree = IntervalTree()
for start, end in intervals:
    tree.addi(start, end)

for q in queries:
    overlapping = tree[q]   # returns a set of Interval objects
    count += len(overlapping)
```

The Python version returns full `Interval` objects that must be counted. The .NET version counts directly in the traversal with no object creation.

## Diagrams

![Query time for 10k points by interval count — .NET stays under 4 seconds at 1M intervals](/projects/11-intervaltree/Diagram1.png)

At 1 million intervals Python takes 2 minutes to answer 10,000 queries; .NET takes under 4 seconds. The logarithmic nature of the tree means neither scales as badly as a linear scan, but Python's per-node overhead keeps it orders of magnitude slower.

![Build time comparison — augmented BST construction vs IntervalTree.addi](/projects/11-intervaltree/Diagram2.png)

Build time shows the same pattern: `IntervalTree.addi` creates a Python object per interval and inserts it into a Python set. The .NET constructor sorts three integer arrays — a cache-friendly operation with zero heap allocation per interval.
