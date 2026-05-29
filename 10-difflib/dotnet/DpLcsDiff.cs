// ============================================================
// milliseconds.dev — .NET vs Python performance benchmarks
// Project : 10 — Sequence diff (difflib)
// Author  : Mo Mand  |  https://milliseconds.dev
//
// DP LCS diff on integer sequences — replaces:
//   Python: difflib.SequenceMatcher(None, a, b, autojunk=False)
//
// Key differences from the Python version:
//   - Single flat int[] buffer preallocated once, reused across all pairs
//     (Python allocates fresh internal state per SequenceMatcher call)
//   - Flat indexing dp[i * stride + j] instead of a 2D array avoids the
//     extra pointer indirection and keeps the hot loop cache-friendly
//   - Integer sequences (vocab=9000) eliminate string comparison overhead
//
// Algorithm: standard edit-distance DP (same LCS equivalence as difflib),
// followed by a traceback to count insertions / deletions / unchanged.
// ============================================================

static class DpLcsDiff
{
    // Maximum sequence length — sequences are generated with 80–200 elements.
    private const int MaxLen = 210;

    // Allocate the reusable flat DP buffer (call once, pass to every Compute call).
    // Python equivalent: SequenceMatcher allocates per call — no pre-allocation.
    public static int[] AllocateBuffer() => new int[MaxLen * MaxLen];

    // Compute diff counts for one pair using the preallocated buffer.
    // Python equivalent:
    //   matcher = SequenceMatcher(None, a, b, autojunk=False)
    //   for tag, i1, i2, j1, j2 in matcher.get_opcodes():
    //       if tag == "equal":   unchanged += i2-i1
    //       elif tag == "insert": insertions += j2-j1
    //       ...
    public static void Compute(int[] a, int[] b, int[] dp,
        ref long ins, ref long dels, ref long unch)
    {
        int n = a.Length, m = b.Length;
        if (n == 0) { ins += m; return; }
        if (m == 0) { dels += n; return; }

        // Fill DP table in the flat buffer: dp[i * MaxLen + j] = edit distance
        for (int i = 0; i <= n; i++) dp[i * MaxLen] = i;
        for (int j = 0; j <= m; j++) dp[j] = j;

        for (int i = 1; i <= n; i++)
        {
            int rowBase = i * MaxLen;
            int prevRow = rowBase - MaxLen;
            for (int j = 1; j <= m; j++)
            {
                if (a[i - 1] == b[j - 1])
                    dp[rowBase + j] = dp[prevRow + j - 1];
                else
                    dp[rowBase + j] = 1 + Math.Min(dp[prevRow + j - 1],
                                          Math.Min(dp[prevRow + j], dp[rowBase + j - 1]));
            }
        }

        // Traceback: walk from (n,m) back to (0,0) counting operation types
        int ci = n, cj = m;
        while (ci > 0 || cj > 0)
        {
            if (ci > 0 && cj > 0 && a[ci - 1] == b[cj - 1])
            {
                unch++; ci--; cj--;
            }
            else if (cj > 0 && (ci == 0 || dp[ci * MaxLen + cj - 1] <= dp[(ci - 1) * MaxLen + cj]))
            {
                ins++; cj--;
            }
            else
            {
                dels++; ci--;
            }
        }
    }

    // Parse a comma-separated integer sequence from a span — no heap allocation for the span itself.
    // Python equivalent: list(map(int, s.split(",")))
    public static int[] ParseInts(ReadOnlySpan<char> span)
    {
        int count = 1;
        foreach (char c in span)
            if (c == ',') count++;
        var result = new int[count];
        int idx = 0;
        foreach (var part in span.Split(','))
            result[idx++] = int.Parse(span[part]);
        return result;
    }
}
