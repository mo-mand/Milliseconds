// ============================================================
// milliseconds.dev — .NET vs Python performance benchmarks
// Project : 09 — Date string parsing
// Author  : Mo Mand  |  https://milliseconds.dev
//
// CLI harness: parse args, load date strings, run the benchmark,
// emit JSON or human-readable results.
// Python equivalent: python/parse_dates.py
// ============================================================

using System;
using System.Diagnostics;
using System.IO;
using System.Text.Json;

bool jsonMode = Array.Exists(args, a => a == "--json");
var pathArgs  = Array.FindAll(args, a => !a.StartsWith("--"));

string inputPath = pathArgs.Length > 0
    ? pathArgs[0]
    : Path.Combine(AppContext.BaseDirectory, "..", "..", "..", "..", "data", "dates_100k.txt");

if (!File.Exists(inputPath))
{
    Console.Error.WriteLine($"File not found: {inputPath}");
    Environment.Exit(1);
}

string[] lines = File.ReadAllLines(inputPath);
if (!jsonMode) Console.WriteLine($"Dates: {lines.Length:N0}");

// DateParser handles all format variants and checksum logic.
// See DateParser.cs for format strings and design notes.
var parser = new DateParser();

var sw = Stopwatch.StartNew();

// Python equivalent:
//   from dateutil.parser import parse
//   for line in lines:
//       dto = parse(line)
//       checksum += dto.year * 10000 + dto.month * 100 + dto.day
long checksum = 0;
int  failed   = 0;
foreach (var line in lines)
{
    if (string.IsNullOrWhiteSpace(line)) continue;
    if (parser.TryParse(line, out var date))
        checksum += date.Year * 10000L + date.Month * 100 + date.Day;
    else
        failed++;
}

sw.Stop();
long elapsedMs = sw.ElapsedMilliseconds;

if (jsonMode)
{
    Console.WriteLine(JsonSerializer.Serialize(new
    {
        dates      = lines.Length,
        checksum,
        failed,
        elapsed_ms = elapsedMs,
    }));
}
else
{
    Console.WriteLine($"Checksum : {checksum:N0}");
    Console.WriteLine($"Failed   : {failed:N0}");
    Console.WriteLine($"Elapsed  : {elapsedMs} ms");
    Console.WriteLine($"Throughput: {lines.Length * 1000.0 / elapsedMs:N0} dates/s");
}
