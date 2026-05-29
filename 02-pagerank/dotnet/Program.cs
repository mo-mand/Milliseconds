// ============================================================
// milliseconds.dev — .NET vs Python performance benchmarks
// Project : 02 — PageRank (sparse matrix power iteration)
// Author  : Mo Mand  |  https://milliseconds.dev
//
// CLI harness: parse args, load graph, run PageRank, emit results.
// Python equivalent: python/pagerank.py
// ============================================================

using System.Diagnostics;
using System.Numerics.Tensors;
using System.Text.Json;

bool jsonMode = args.Contains("--json");
var pathArgs  = args.Where(a => !a.StartsWith("--")).ToArray();

var dataPath = pathArgs.Length > 0 ? pathArgs[0]
    : Path.Combine(AppContext.BaseDirectory, "..", "..", "..", "..", "data", "links.tsv");

if (!File.Exists(dataPath))
{
    Console.Error.WriteLine($"Data file not found: {dataPath}");
    Console.Error.WriteLine("Run: python python/download_data.py");
    return 1;
}

void Log(string msg) { if (!jsonMode) Console.WriteLine(msg); }

Log($"Loading graph from: {dataPath}");
var t0 = Stopwatch.GetTimestamp();

// Load the graph into CSR (Compressed Sparse Row) format.
// Python equivalent: G = networkx.DiGraph(); G.add_edges_from(...)
var (rowPtr, colIdx, n) = CsrGraph.Load(dataPath);
double loadMs = Stopwatch.GetElapsedTime(t0).TotalMilliseconds;
Log($"Nodes: {n:N0}   Edges: {colIdx.Length:N0}   (loaded in {loadMs:F0} ms)");

Log("Running PageRank (damping=0.85, tol=1e-6) ...");

// Python equivalent: nx.pagerank(G, alpha=0.85, tol=1e-6, max_iter=100)
var sw = Stopwatch.StartNew();
var (rank, iter, delta) = PageRank.Compute(rowPtr, colIdx, n);
sw.Stop();
double computeMs = sw.Elapsed.TotalMilliseconds;

var top10 = rank.Select((r, i) => (r, i))
                .OrderByDescending(x => x.r)
                .Take(10)
                .ToArray();

if (jsonMode)
{
    Console.WriteLine(JsonSerializer.Serialize(new
    {
        nodes      = n,
        edges      = colIdx.Length,
        load_ms    = Math.Round(loadMs, 1),
        compute_ms = Math.Round(computeMs, 1),
        iterations = iter,
        delta,
        top10 = top10.Select(x => new { node = x.i, score = x.r }).ToArray(),
    }));
}
else
{
    Log($"\nConverged: {iter} iterations  delta={delta:E2}");
    Log($"Elapsed  : {computeMs:F1} ms\n");
    Log($"{"Rank",-5} {"Node",10} {"Score",14}");
    Log(new string('-', 32));
    for (int k = 0; k < top10.Length; k++)
        Log($"{k + 1,-5} {top10[k].i,10} {top10[k].r,14:E6}");
}

return 0;
