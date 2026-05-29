// ============================================================
// milliseconds.dev — .NET vs Python performance benchmarks
// Project : 11 — Interval tree point queries
// Author  : Mo Mand  |  https://milliseconds.dev
//
// Array-based augmented interval tree — replaces:
//   Python: intervaltree.IntervalTree  (pure-Python, sorted-list backed)
//
// Key differences from the Python version:
//   - Three parallel int[] arrays instead of a set of Interval objects —
//     no heap allocation per interval, no Python object boxing
//   - Implicit BST: array sorted by start, mid = (lo+hi)/2 is the root
//   - maxEnd[] augmentation enables subtree pruning: if maxEnd[mid] < q,
//     no interval in the entire subtree can contain q
//   - Python's IntervalTree.at(q) allocates a new set per query;
//     CountRec accumulates into a single int on the stack
//
// Python inclusive convention: tree.addi(begin, end+1, i) — end+1 because
// intervaltree uses [begin, end) exclusive. Our arrays store [begin, end]
// inclusive, so we compare start[mid] <= q <= end[mid].
// ============================================================

class AugmentedIntervalTree
{
    private readonly int[] _start;
    private readonly int[] _end;
    private readonly int[] _maxEnd;
    private readonly int   _n;

    // Build the tree from raw parallel arrays.
    // Python equivalent: tree.addi(begin, end+1, i) for i, (begin, end) in enumerate(intervals)
    public AugmentedIntervalTree(int[] starts, int[] ends)
    {
        _n = starts.Length;

        // Sort by start coordinate to establish the implicit BST ordering.
        int[] idx = new int[_n];
        for (int i = 0; i < _n; i++) idx[i] = i;
        Array.Sort(idx, (a, b) => starts[a].CompareTo(starts[b]));

        _start  = new int[_n];
        _end    = new int[_n];
        _maxEnd = new int[_n];
        for (int i = 0; i < _n; i++)
        {
            _start[i] = starts[idx[i]];
            _end[i]   = ends[idx[i]];
        }

        // Fill maxEnd[] bottom-up so every node stores the maximum end value
        // in its subtree — the key to O(log n + k) pruning during queries.
        BuildMaxEnd(0, _n - 1);
    }

    // Count intervals that contain point q (i.e. start <= q <= end).
    // Python equivalent: len(tree.at(q))
    public int CountOverlaps(int q)
    {
        int count = 0;
        CountRec(0, _n - 1, q, ref count);
        return count;
    }

    // Recursively fill maxEnd[mid] = max end value in subtree rooted at mid.
    // Returns the max so the parent can update its own maxEnd without re-scanning.
    private int BuildMaxEnd(int lo, int hi)
    {
        if (lo > hi) return 0;
        int mid      = (lo + hi) / 2;
        int leftMax  = BuildMaxEnd(lo, mid - 1);
        int rightMax = BuildMaxEnd(mid + 1, hi);
        int mx       = Math.Max(_end[mid], Math.Max(leftMax, rightMax));
        _maxEnd[mid] = mx;
        return mx;
    }

    // Recursive point-query with two pruning rules:
    //   1. maxEnd[mid] < q  → entire subtree ends before q, skip it
    //   2. start[mid] > q   → right subtree starts after q, skip it (BST property)
    private void CountRec(int lo, int hi, int q, ref int count)
    {
        if (lo > hi) return;
        int mid = (lo + hi) / 2;

        if (_maxEnd[mid] < q) return;

        // Check left subtree first (may prune right after checking current node)
        CountRec(lo, mid - 1, q, ref count);

        if (_start[mid] <= q && _end[mid] >= q) count++;

        // If current node's start > q, all right-subtree nodes also start > q
        if (_start[mid] > q) return;

        CountRec(mid + 1, hi, q, ref count);
    }
}
