// ============================================================
// milliseconds.dev — .NET vs Python performance benchmarks
// Project : 02 — PageRank (sparse matrix power iteration)
// Author  : Mo Mand  |  https://milliseconds.dev
//
// CSR power-iteration PageRank — replaces:
//   Python: networkx.pagerank(G, alpha=0.85, tol=1e-6, max_iter=100)
//
// Key differences from the Python version:
//   - CSR (Compressed Sparse Row) avoids NetworkX's dict-of-dict adjacency
//   - TensorPrimitives.Divide / Sum use AVX-512 SIMD on modern hardware
//   - No Python GIL, no boxed float objects, no dictionary lookups per edge
//   - double[] for precision parity with Python's float64
// ============================================================

using System.Numerics.Tensors;

static class PageRank
{
    private const double Damping = 0.85;
    private const double Tol     = 1e-6;
    private const int    MaxIter = 100;

    // Run power iteration on the CSR graph.
    // Python equivalent: nx.pagerank(G, alpha=0.85, tol=1e-6, max_iter=100)
    public static (double[] rank, int iter, double delta) Compute(int[] rowPtr, int[] colIdx, int n)
    {
        var outDeg = new int[n];
        for (int u = 0; u < n; u++)
            outDeg[u] = rowPtr[u + 1] - rowPtr[u];

        double[] rank    = new double[n];
        double[] newRank = new double[n];
        Array.Fill(rank, 1.0 / n);

        int    iter  = 0;
        double delta = double.MaxValue;

        while (iter < MaxIter && delta > Tol)
        {
            // Dangling node contribution: nodes with no outgoing edges spread
            // their rank uniformly — same as NetworkX's dangling_nodes treatment.
            double danglingSum = 0.0;
            for (int u = 0; u < n; u++)
                if (outDeg[u] == 0) danglingSum += rank[u];

            double baseVal = (1.0 - Damping + Damping * danglingSum) / n;
            Array.Fill(newRank, baseVal);

            // Distribute rank along out-edges (CSR row traversal)
            for (int u = 0; u < n; u++)
            {
                int start = rowPtr[u];
                int end   = rowPtr[u + 1];
                if (start == end) continue;

                double contrib = Damping * rank[u] / (end - start);
                foreach (int v in colIdx.AsSpan(start, end - start))
                    newRank[v] += contrib;
            }

            // L1-normalise using TensorPrimitives (SIMD AVX-512 on supported hardware)
            double total = TensorPrimitives.Sum<double>(newRank);
            TensorPrimitives.Divide<double>(newRank, total, newRank);

            // Convergence check (L1 norm of rank change)
            delta = 0.0;
            for (int i = 0; i < n; i++)
                delta += Math.Abs(newRank[i] - rank[i]);

            (rank, newRank) = (newRank, rank);
            iter++;
        }

        return (rank, iter, delta);
    }
}
