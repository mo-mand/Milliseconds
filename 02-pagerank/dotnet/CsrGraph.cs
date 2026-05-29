// ============================================================
// milliseconds.dev — .NET vs Python performance benchmarks
// Project : 02 — PageRank (sparse matrix power iteration)
// Author  : Mo Mand  |  https://milliseconds.dev
//
// CSR graph loader — replaces:
//   Python: G = networkx.DiGraph(); (implicit dict-of-dict adjacency)
//
// CSR (Compressed Sparse Row) stores the graph as two int[]:
//   rowPtr[u]..rowPtr[u+1] = range of neighbours of node u in colIdx
// This layout gives O(degree) neighbour traversal with sequential memory
// access — far cheaper than Python's dict lookup per neighbour.
// ============================================================

static class CsrGraph
{
    // Load a tab-separated edge list into CSR format.
    // Python equivalent: G.add_edges_from((int(u), int(v)) for u, v in ...)
    public static (int[] rowPtr, int[] colIdx, int n) Load(string path)
    {
        var edges = new List<(int u, int v)>(8_000_000);
        int maxId = 0;

        foreach (var line in File.ReadLines(path))
        {
            if (line.Length == 0 || line[0] == '#') continue;
            int tab = line.IndexOf('\t');
            if (tab < 0) continue;
            if (!int.TryParse(line.AsSpan(0, tab), out int u)) continue;
            if (!int.TryParse(line.AsSpan(tab + 1), out int v)) continue;
            edges.Add((u, v));
            if (u > maxId) maxId = u;
            if (v > maxId) maxId = v;
        }

        int n   = maxId + 1;
        var deg = new int[n];
        foreach (var (u, _) in edges) deg[u]++;

        // Build rowPtr from degree counts (prefix sum)
        var rowPtr = new int[n + 1];
        for (int i = 0; i < n; i++) rowPtr[i + 1] = rowPtr[i] + deg[i];

        // Fill colIdx using a position cursor per row
        var colIdx = new int[edges.Count];
        var pos    = (int[])rowPtr.Clone();
        foreach (var (u, v) in edges) colIdx[pos[u]++] = v;

        return (rowPtr, colIdx, n);
    }
}
