// ============================================================
// milliseconds.dev — .NET vs Python performance benchmarks
// Project : 05 — Full-text search (Whoosh → Lucene.NET)
// Author  : Mo Mand  |  https://milliseconds.dev
//
// CLI harness: parse args, run index + search phases, emit results.
// Python equivalent: python/search_bench.py
// ============================================================

using System.Diagnostics;
using System.Text.Json;

bool jsonMode = args.Contains("--json");
var pathArgs  = args.Where(a => !a.StartsWith("--")).ToArray();

var docsPath = pathArgs.Length > 0 ? pathArgs[0]
    : Path.Combine(AppContext.BaseDirectory, "..", "..", "..", "..", "data", "docs_10k.jsonl");

if (!File.Exists(docsPath))
{
    Console.Error.WriteLine($"File not found: {docsPath}");
    Console.Error.WriteLine("Run: python python/build_corpus.py");
    return 1;
}

void Log(string msg) { if (!jsonMode) Console.WriteLine(msg); }

// SearchBenchmark runs both phases in a temp directory that is cleaned up on exit.
// See SearchBenchmark.cs for indexing and search logic.
var bench = new SearchBenchmark();

Log($"Indexing: {docsPath}");

// Python equivalent:
//   ix = whoosh.index.create_in(tmpdir, schema)
//   writer = ix.writer()
//   for doc in docs: writer.add_document(**doc)
//   writer.commit()
var indexResult = bench.Index(docsPath);
Log($"Indexed {indexResult.DocCount:N0} docs in {indexResult.IndexMs:F1} ms  ({indexResult.DocCount / (indexResult.IndexMs / 1000):F0} docs/s)");

// Python equivalent:
//   with ix.searcher() as searcher:
//       for query in queries * ROUNDS:
//           results = searcher.search(QueryParser("body", schema).parse(query))
var searchResult = bench.Search();
Log($"Searched {searchResult.TotalQueries:N0} queries in {searchResult.SearchMs:F1} ms  ({searchResult.TotalQueries / (searchResult.SearchMs / 1000):F0} queries/s)");
Log($"Total hits: {searchResult.TotalHits:N0}");

bench.Dispose();

if (jsonMode)
{
    Console.WriteLine(JsonSerializer.Serialize(new
    {
        docs          = indexResult.DocCount,
        index_ms      = Math.Round(indexResult.IndexMs, 1),
        search_ms     = Math.Round(searchResult.SearchMs, 1),
        total_queries = searchResult.TotalQueries,
        total_hits    = searchResult.TotalHits,
    }));
}

return 0;
