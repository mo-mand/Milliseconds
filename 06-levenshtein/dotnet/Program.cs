// ============================================================
// milliseconds.dev — .NET vs Python performance benchmarks
// Project : 06 — Levenshtein edit distance
// Author  : Mo Mand  |  https://milliseconds.dev
//
// CLI harness: parse args, load word pairs, run the benchmark,
// emit JSON or human-readable results.
// Python equivalent: python/levenshtein.py
// ============================================================

using System.Buffers;
using System.Diagnostics;
using System.Text.Json;

bool jsonMode = args.Contains("--json");
var pathArgs  = args.Where(a => !a.StartsWith("--")).ToArray();

var pairsPath = pathArgs.Length > 0 ? pathArgs[0]
    : Path.Combine(AppContext.BaseDirectory, "..", "..", "..", "..", "data", "pairs_100k.tsv");

if (!File.Exists(pairsPath))
{
    Console.Error.WriteLine($"File not found: {pairsPath}");
    Console.Error.WriteLine("Run: python python/build_pairs.py");
    return 1;
}

void Log(string msg) { if (!jsonMode) Console.WriteLine(msg); }

Log($"Loading pairs from: {pairsPath}");
var lines = File.ReadAllLines(pairsPath);
Log($"Pairs: {lines.Length:N0}");

// ArrayPool buffer reused across all calls — Python allocates per-call state.
// See Levenshtein.cs for the algorithm.
var pool   = ArrayPool<int>.Shared;
var buffer = pool.Rent(512);

var sw = Stopwatch.StartNew();
long checksum = 0;

foreach (var line in lines)
{
    int tab = line.IndexOf('\t');
    if (tab < 0) continue;
    checksum += Levenshtein.Distance(line.AsSpan(0, tab), line.AsSpan(tab + 1), buffer);
}

sw.Stop();
pool.Return(buffer);

double elapsedMs = sw.Elapsed.TotalMilliseconds;

if (jsonMode)
{
    Console.WriteLine(JsonSerializer.Serialize(new
    {
        pairs      = lines.Length,
        checksum,
        elapsed_ms = Math.Round(elapsedMs, 1),
    }));
}
else
{
    Log($"\nChecksum  : {checksum:N0}");
    Log($"Elapsed   : {elapsedMs:F1} ms");
    Log($"Throughput: {lines.Length / (elapsedMs / 1000):F0} pairs/s");
}

return 0;
