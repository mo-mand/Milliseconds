// ============================================================
// milliseconds.dev — .NET vs Python performance benchmarks
// Project : 13 — HTML parsing (BeautifulSoup4 vs AngleSharp)
// Author  : Mo Mand  |  https://milliseconds.dev
//
// Per document: parse HTML -> find all <a> hrefs
//               -> count <td> cells -> extract <h1> text
//
// Python equivalent: python/parse.py
// ============================================================

using System.Diagnostics;
using System.Text.Json;
using AngleSharp;
using AngleSharp.Html.Parser;

bool   jsonMode = Array.Exists(args, a => a == "--json");
string[] rest   = Array.FindAll(args, a => !a.StartsWith("--"));

string dataDir = rest.Length > 0
    ? rest[0]
    : Path.Combine(AppContext.BaseDirectory, "..", "..", "..", "..", "data", "docs_5k");

if (!Directory.Exists(dataDir))
{
    Console.Error.WriteLine($"Directory not found: {dataDir}");
    Environment.Exit(1);
}

var files = Directory.GetFiles(dataDir, "*.html", SearchOption.TopDirectoryOnly);
Array.Sort(files);

if (files.Length == 0)
{
    Console.Error.WriteLine($"No .html files in {dataDir}");
    Environment.Exit(1);
}

// Pre-load all documents so disk I/O doesn't skew timing
var raw = new string[files.Length];
for (int i = 0; i < files.Length; i++)
    raw[i] = File.ReadAllText(files[i]);

if (!jsonMode)
    Console.WriteLine($"Docs: {raw.Length:N0}");

// AngleSharp parser — reuse a single instance across all documents
var parser = new HtmlParser();

long totalHrefs = 0;
long totalTds   = 0;

var sw = Stopwatch.StartNew();

for (int i = 0; i < raw.Length; i++)
{
    using var doc = parser.ParseDocument(raw[i]);

    foreach (var a in doc.QuerySelectorAll("a[href]"))
        totalHrefs++;

    totalTds += doc.QuerySelectorAll("td").Length;

    // Touch h1 text to match Python's .get_text() call
    var h1 = doc.QuerySelector("h1");
    _ = h1?.TextContent?.Trim();
}

sw.Stop();
long elapsedMs = sw.ElapsedMilliseconds;

if (jsonMode)
{
    Console.WriteLine(JsonSerializer.Serialize(new
    {
        docs         = raw.Length,
        elapsed_ms   = (double)elapsedMs,
        total_hrefs  = totalHrefs,
        total_tds    = totalTds,
    }));
}
else
{
    Console.WriteLine($"Elapsed: {elapsedMs:N0} ms  ({(double)elapsedMs / raw.Length:F2} ms/doc)");
    Console.WriteLine($"Hrefs  : {totalHrefs:N0}   TDs: {totalTds:N0}");
}
