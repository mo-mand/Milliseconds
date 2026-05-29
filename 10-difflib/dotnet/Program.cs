// ============================================================
// milliseconds.dev — .NET vs Python performance benchmarks
// Project : 10 — Sequence diff (difflib)
// Author  : Mo Mand  |  https://milliseconds.dev
//
// CLI harness: parse args, load integer-sequence pairs, run the benchmark,
// emit JSON or human-readable results.
// Python equivalent: python/diff_texts.py
// ============================================================

using System;
using System.Diagnostics;
using System.IO;
using System.Text.Json;

bool jsonMode = Array.Exists(args, a => a == "--json");
var pathArgs  = Array.FindAll(args, a => !a.StartsWith("--"));

string inputPath = pathArgs.Length > 0
    ? pathArgs[0]
    : Path.Combine(AppContext.BaseDirectory, "..", "..", "..", "..", "data", "pairs_10k.tsv");

if (!File.Exists(inputPath))
{
    Console.Error.WriteLine($"File not found: {inputPath}");
    Environment.Exit(1);
}

string[] lines = File.ReadAllLines(inputPath);
if (!jsonMode) Console.WriteLine($"Pairs: {lines.Length:N0}");

// Pre-parse all pairs before timing starts.
// Python equivalent: pairs = [(list(map(int, a)), list(map(int, b))) for ...]
var pairs = new (int[] a, int[] b)[lines.Length];
int validCount = 0;
foreach (var line in lines)
{
    int tab = line.IndexOf('\t');
    if (tab < 0) continue;
    pairs[validCount++] = (DpLcsDiff.ParseInts(line.AsSpan(0, tab)),
                           DpLcsDiff.ParseInts(line.AsSpan(tab + 1)));
}

// Single preallocated DP buffer — the key memory optimization.
// Python allocates a fresh internal state object per SequenceMatcher call.
// See DpLcsDiff.cs for the algorithm design.
var dpBuf = DpLcsDiff.AllocateBuffer();

var sw = Stopwatch.StartNew();

long insertions = 0;
long deletions  = 0;
long unchanged  = 0;

// Python equivalent:
//   for a, b in pairs:
//       matcher = difflib.SequenceMatcher(None, a, b, autojunk=False)
//       for tag, i1, i2, j1, j2 in matcher.get_opcodes(): ...
for (int p = 0; p < validCount; p++)
{
    var (a, b) = pairs[p];
    DpLcsDiff.Compute(a, b, dpBuf, ref insertions, ref deletions, ref unchanged);
}

sw.Stop();
long elapsedMs = sw.ElapsedMilliseconds;
long checksum  = insertions + deletions;

if (jsonMode)
{
    Console.WriteLine(JsonSerializer.Serialize(new
    {
        pairs      = validCount,
        insertions,
        deletions,
        unchanged,
        checksum,
        elapsed_ms = elapsedMs,
    }));
}
else
{
    Console.WriteLine($"Insertions : {insertions:N0}");
    Console.WriteLine($"Deletions  : {deletions:N0}");
    Console.WriteLine($"Unchanged  : {unchanged:N0}");
    Console.WriteLine($"Elapsed    : {elapsedMs} ms");
    Console.WriteLine($"Throughput : {validCount * 1000.0 / elapsedMs:N0} pairs/s");
}
