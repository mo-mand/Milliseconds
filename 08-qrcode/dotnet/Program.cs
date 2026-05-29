// ============================================================
// milliseconds.dev — .NET vs Python performance benchmarks
// Project : 08 — QR code generation
// Author  : Mo Mand  |  https://milliseconds.dev
//
// CLI harness: parse args, load input strings, run the benchmark,
// emit JSON or human-readable results.
// Python equivalent: python/generate.py
// ============================================================

using System;
using System.Diagnostics;
using System.IO;
using System.Text.Json;

bool jsonMode = Array.Exists(args, a => a == "--json");
var pathArgs  = Array.FindAll(args, a => !a.StartsWith("--"));

string inputPath = pathArgs.Length > 0
    ? pathArgs[0]
    : Path.Combine(AppContext.BaseDirectory, "..", "..", "..", "..", "data", "inputs_10k.txt");

if (!File.Exists(inputPath))
{
    Console.Error.WriteLine($"File not found: {inputPath}");
    Environment.Exit(1);
}

string[] inputs = File.ReadAllLines(inputPath);
if (!jsonMode) Console.WriteLine($"Inputs: {inputs.Length:N0}");

// QrAnalyzer owns the QRCodeGenerator instance and knows the quiet-zone offset.
// See QrAnalyzer.cs for details.
var analyzer = new QrAnalyzer();

var sw = Stopwatch.StartNew();

// Python equivalent:
//   qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, border=0)
//   for text in inputs:
//       qr.clear()
//       qr.add_data(text)
//       qr.make(fit=True)
//       matrix = qr.get_matrix()
long totalDarkModules = 0;
int  totalSize        = 0;

foreach (var text in inputs)
{
    if (string.IsNullOrWhiteSpace(text)) continue;
    var result = analyzer.Analyze(text);
    totalDarkModules += result.DarkModules;
    totalSize        += result.Size;
}

sw.Stop();
long elapsedMs = sw.ElapsedMilliseconds;

if (jsonMode)
{
    Console.WriteLine(JsonSerializer.Serialize(new
    {
        codes      = inputs.Length,
        dark_mods  = totalDarkModules,
        total_size = totalSize,
        elapsed_ms = elapsedMs,
    }));
}
else
{
    Console.WriteLine($"Codes       : {inputs.Length:N0}");
    Console.WriteLine($"Dark modules: {totalDarkModules:N0}");
    Console.WriteLine($"Elapsed     : {elapsedMs} ms");
    Console.WriteLine($"Throughput  : {inputs.Length * 1000.0 / elapsedMs:N0} codes/s");
}
