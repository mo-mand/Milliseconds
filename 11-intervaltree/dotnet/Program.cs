// ============================================================
// milliseconds.dev — .NET vs Python performance benchmarks
// Project : 11 — Interval tree point queries
// Author  : Mo Mand  |  https://milliseconds.dev
//
// CLI harness: parse args, load intervals and queries, run the benchmark,
// emit JSON or human-readable results.
// Python equivalent: python/query_tree.py
// ============================================================

using System;
using System.Diagnostics;
using System.IO;
using System.Text.Json;

bool jsonMode = Array.Exists(args, a => a == "--json");
var pathArgs  = Array.FindAll(args, a => !a.StartsWith("--"));

string inputPath = pathArgs.Length > 0
    ? pathArgs[0]
    : Path.Combine(AppContext.BaseDirectory, "..", "..", "..", "..", "data", "data_100k.tsv");

if (!File.Exists(inputPath))
{
    Console.Error.WriteLine($"File not found: {inputPath}");
    Environment.Exit(1);
}

// File format: "begin\tend" lines, blank line separator, then query points one per line.
// Python equivalent: lines = data_path.read_text().splitlines(); sep = lines.index("")
string[] allLines = File.ReadAllLines(inputPath);
int sep = Array.IndexOf(allLines, "");

int[] starts = new int[sep];
int[] ends   = new int[sep];
for (int i = 0; i < sep; i++)
{
    int tab = allLines[i].IndexOf('\t');
    starts[i] = int.Parse(allLines[i].AsSpan(0, tab));
    ends[i]   = int.Parse(allLines[i].AsSpan(tab + 1));
}

int qCount = allLines.Length - sep - 1;
int[] queries = new int[qCount];
for (int i = 0; i < qCount; i++)
    queries[i] = int.Parse(allLines[sep + 1 + i]);

if (!jsonMode) Console.WriteLine($"Intervals: {sep:N0}  Queries: {qCount:N0}");

// ---- Build ------------------------------------------------------------------
// Python equivalent:
//   tree = IntervalTree()
//   for i, (begin, end) in enumerate(intervals):
//       tree.addi(begin, end + 1, i)
var buildSw = Stopwatch.StartNew();
var tree = new AugmentedIntervalTree(starts, ends);
buildSw.Stop();

// ---- Query ------------------------------------------------------------------
// Python equivalent:
//   for q in queries:
//       checksum += len(tree.at(q))
var querySw = Stopwatch.StartNew();
long checksum = 0;
foreach (int q in queries)
    checksum += tree.CountOverlaps(q);
querySw.Stop();

long buildMs = buildSw.ElapsedMilliseconds;
long queryMs = querySw.ElapsedMilliseconds;

if (jsonMode)
{
    Console.WriteLine(JsonSerializer.Serialize(new
    {
        intervals  = sep,
        queries    = qCount,
        checksum,
        build_ms   = buildMs,
        query_ms   = queryMs,
        elapsed_ms = buildMs + queryMs,
    }));
}
else
{
    Console.WriteLine($"Checksum  : {checksum:N0}");
    Console.WriteLine($"Build     : {buildMs} ms");
    Console.WriteLine($"Query     : {queryMs} ms");
    Console.WriteLine($"Throughput: {qCount * 1000.0 / Math.Max(queryMs, 1):N0} queries/s");
}
