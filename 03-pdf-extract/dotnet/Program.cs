// ============================================================
// milliseconds.dev — .NET vs Python performance benchmarks
// Project : 03 — PDF text extraction
// Author  : Mo Mand  |  https://milliseconds.dev
//
// CLI harness: parse args, enumerate PDF files, run the benchmark,
// emit JSON or human-readable results.
// Python equivalent: python/extract.py
// ============================================================

using System.Diagnostics;
using System.Text.Json;

bool jsonMode = args.Contains("--json");
var pathArgs  = args.Where(a => !a.StartsWith("--")).ToArray();

var pdfDir = pathArgs.Length > 0 ? pathArgs[0]
    : Path.Combine(AppContext.BaseDirectory, "..", "..", "..", "..", "data", "pdfs");

if (!Directory.Exists(pdfDir))
{
    Console.Error.WriteLine($"Directory not found: {pdfDir}");
    Console.Error.WriteLine("Run: python python/download_data.py");
    return 1;
}

var files = Directory.GetFiles(pdfDir, "*.pdf", SearchOption.TopDirectoryOnly);
if (files.Length == 0)
{
    Console.Error.WriteLine($"No PDF files found in {pdfDir}");
    return 1;
}

void Log(string msg) { if (!jsonMode) Console.WriteLine(msg); }
Log($"Extracting text from {files.Length} PDFs in: {pdfDir}");

// PdfExtractor wraps PdfPig and accumulates char/page counts.
// See PdfExtractor.cs for the extraction logic.
var extractor = new PdfExtractor();

var sw = Stopwatch.StartNew();

long totalChars = 0;
long totalPages = 0;
int  errors     = 0;

// Python equivalent:
//   for path in pdfs:
//       doc = fitz.open(path)
//       for page in doc: total_chars += len(page.get_text())
foreach (var path in files)
{
    var result = extractor.Extract(path);
    totalChars += result.Chars;
    totalPages += result.Pages;
    if (!result.Ok) errors++;
}

sw.Stop();
double elapsedMs = sw.Elapsed.TotalMilliseconds;

if (jsonMode)
{
    Console.WriteLine(JsonSerializer.Serialize(new
    {
        files     = files.Length,
        pages     = totalPages,
        chars     = totalChars,
        errors,
        elapsed_ms = Math.Round(elapsedMs, 1),
    }));
}
else
{
    Log($"\nFiles   : {files.Length}");
    Log($"Pages   : {totalPages:N0}");
    Log($"Chars   : {totalChars:N0}");
    Log($"Errors  : {errors}");
    Log($"Elapsed : {elapsedMs:F1} ms  ({elapsedMs / files.Length:F1} ms/file)");
}

return 0;
