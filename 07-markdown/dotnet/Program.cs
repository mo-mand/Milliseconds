// ============================================================
// milliseconds.dev — .NET vs Python performance benchmarks
// Project : 07 — Markdown rendering
// Author  : Mo Mand  |  https://milliseconds.dev
//
// CLI harness: parse args, load documents, run the benchmark,
// emit JSON or human-readable results.
// Python equivalent: python/render.py
// ============================================================

using System;
using System.Diagnostics;
using System.IO;
using System.Text.Json;

bool jsonMode = Array.Exists(args, a => a == "--json");
var pathArgs  = Array.FindAll(args, a => !a.StartsWith("--"));

string inputPath = pathArgs.Length > 0
    ? pathArgs[0]
    : Path.Combine(AppContext.BaseDirectory, "..", "..", "..", "..", "data", "docs_10k.txt");

if (!File.Exists(inputPath))
{
    Console.Error.WriteLine($"File not found: {inputPath}");
    Environment.Exit(1);
}

// Each line is one Markdown document.
// Python equivalent: docs = corpus_path.read_text().splitlines()
string[] docs = File.ReadAllLines(inputPath);
if (!jsonMode) Console.WriteLine($"Docs: {docs.Length:N0}");

// Build the pipeline once and reuse — Markdig recommends a single pipeline instance.
// See MarkdownRenderer.cs for pipeline setup.
var renderer = new MarkdownRenderer();

var sw = Stopwatch.StartNew();

// Python equivalent:
//   md = mistune.create_markdown()
//   for doc in docs:
//       html = md(doc)
//       total_html_chars += len(html)
long totalHtmlChars = 0;
foreach (var doc in docs)
    totalHtmlChars += renderer.Render(doc).Length;

sw.Stop();
long elapsedMs = sw.ElapsedMilliseconds;

if (jsonMode)
{
    Console.WriteLine(JsonSerializer.Serialize(new
    {
        docs       = docs.Length,
        html_chars = totalHtmlChars,
        elapsed_ms = elapsedMs,
    }));
}
else
{
    Console.WriteLine($"HTML chars : {totalHtmlChars:N0}");
    Console.WriteLine($"Elapsed    : {elapsedMs} ms");
    Console.WriteLine($"Throughput : {docs.Length * 1000.0 / elapsedMs:N0} docs/s");
}
