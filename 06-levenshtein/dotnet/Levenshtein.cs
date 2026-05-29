// ============================================================
// milliseconds.dev — .NET vs Python performance benchmarks
// Project : 06 — Levenshtein edit distance
// Author  : Mo Mand  |  https://milliseconds.dev
//
// Wagner-Fischer edit distance — replaces:
//   Python: textdistance.Levenshtein(external=False).distance(a, b)
//
// Key differences from the Python version:
//   - Single preallocated row (ArrayPool<int>) shared across all calls
//     instead of a fresh O(m*n) matrix per call
//   - ReadOnlySpan<char> gives zero-copy access to substrings
//   - JIT compiles to tight native code; Python dispatches boxed objects
//
// Space: O(min(|a|, |b|)) — one row only, not the full matrix
// Time:  O(|a| * |b|)
// ============================================================

using System.Buffers;

static class Levenshtein
{
    // Computes the edit distance between a and b using a single reused row.
    // `row` must have capacity >= min(a.Length, b.Length) + 1.
    // Python equivalent: algo.distance(a, b)  where algo = Levenshtein(external=False)
    public static int Distance(ReadOnlySpan<char> a, ReadOnlySpan<char> b, int[] row)
    {
        // Always iterate over the shorter string as the column dimension
        // to keep the row buffer as small as possible.
        if (a.Length < b.Length) { var t = a; a = b; b = t; }

        int m = a.Length;
        int n = b.Length;
        if (n == 0) return m;
        if (m == 0) return n;

        // row[j] = distance("", b[0..j])
        for (int j = 0; j <= n; j++) row[j] = j;

        for (int i = 1; i <= m; i++)
        {
            int prev = i;   // row[0] for this row = cost of deleting i chars
            for (int j = 1; j <= n; j++)
            {
                int cost = a[i - 1] == b[j - 1] ? 0 : 1;
                int cur  = Math.Min(
                               Math.Min(row[j] + 1,   // deletion
                                        prev  + 1),   // insertion
                               row[j - 1] + cost);    // substitution
                row[j - 1] = prev;
                prev = cur;
            }
            row[n] = prev;
        }
        return row[n];
    }
}
