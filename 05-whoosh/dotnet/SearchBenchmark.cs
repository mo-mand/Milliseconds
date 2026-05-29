// ============================================================
// milliseconds.dev — .NET vs Python performance benchmarks
// Project : 05 — Full-text search (Whoosh → Lucene.NET)
// Author  : Mo Mand  |  https://milliseconds.dev
//
// Lucene.NET search benchmark — replaces:
//   Python: Whoosh (pure-Python BM25 full-text search)
//
// Key differences from the Python version:
//   - Lucene.NET is 100% managed C# — no JVM, no native binaries
//   - StandardAnalyzer + BM25 scoring — same ranking algorithm as Whoosh
//   - FSDirectory uses OS file cache efficiently; Whoosh uses mmap
//   - RAMBufferSizeMB = 256 matches Whoosh's default limitmb setting
//   - Temp index directory is cleaned up in Dispose()
// ============================================================

using Lucene.Net.Analysis.Standard;
using Lucene.Net.Documents;
using Lucene.Net.Index;
using Lucene.Net.QueryParsers.Classic;
using Lucene.Net.Search;
using Lucene.Net.Store;
using Lucene.Net.Util;
using System.Text.Json;

class SearchBenchmark : IDisposable
{
    private const LuceneVersion Ver = LuceneVersion.LUCENE_48;

    // Queries derived from high-frequency content words in the corpus.
    // Python equivalent: same list passed to QueryParser("body", schema).parse(q)
    private static readonly string[] Queries =
    [
        "government", "president", "market", "million", "company",
        "system", "national", "american", "police", "report",
        "official", "state", "party", "people", "program",
        "research", "university", "students", "science", "health",
    ];
    private const int Rounds = 50;   // 50 × 20 queries = 1,000 total

    private readonly string     _indexDir;
    private readonly FSDirectory _fsDir;
    private readonly StandardAnalyzer _analyzer;
    private IndexSearcher? _searcher;

    public SearchBenchmark()
    {
        _indexDir = Path.Combine(Path.GetTempPath(), $"lucene_{Guid.NewGuid():N}");
        System.IO.Directory.CreateDirectory(_indexDir);
        _analyzer = new StandardAnalyzer(Ver);
        _fsDir    = FSDirectory.Open(_indexDir);
    }

    public readonly record struct IndexResult(int DocCount, double IndexMs);
    public readonly record struct SearchResult(int TotalQueries, long TotalHits, double SearchMs);

    // Phase 1: index all documents from the JSONL file.
    // Python equivalent: writer = ix.writer(); writer.add_document(...); writer.commit()
    public IndexResult Index(string docsPath)
    {
        var config = new IndexWriterConfig(Ver, _analyzer)
        {
            OpenMode        = OpenMode.CREATE,
            RAMBufferSizeMB = 256,
        };
        var writer = new IndexWriter(_fsDir, config);
        var lines  = File.ReadAllLines(docsPath);
        var sw     = System.Diagnostics.Stopwatch.StartNew();

        foreach (var line in lines)
        {
            if (string.IsNullOrWhiteSpace(line)) continue;
            using var doc  = JsonDocument.Parse(line);
            var root       = doc.RootElement;
            var luceneDoc  = new Document
            {
                new StringField("id",    root.GetProperty("id").GetString()!,    Field.Store.YES),
                new TextField ("title",  root.GetProperty("title").GetString()!, Field.Store.YES),
                new TextField ("body",   root.GetProperty("body").GetString()!,  Field.Store.NO),
            };
            writer.AddDocument(luceneDoc);
        }

        writer.Commit();
        writer.Dispose();

        int docCount = lines.Count(l => !string.IsNullOrWhiteSpace(l));
        _searcher = new IndexSearcher(DirectoryReader.Open(_fsDir));
        return new IndexResult(docCount, sw.Elapsed.TotalMilliseconds);
    }

    // Phase 2: run 1,000 queries against the index.
    // Python equivalent:
    //   with ix.searcher() as s:
    //       for _ in range(ROUNDS):
    //           for q in queries:
    //               results = s.search(parser.parse(q), limit=10)
    public SearchResult Search()
    {
        var parser    = new QueryParser(Ver, "body", _analyzer);
        long total    = 0;
        var sw        = System.Diagnostics.Stopwatch.StartNew();

        for (int r = 0; r < Rounds; r++)
            foreach (var q in Queries)
                total += _searcher!.Search(parser.Parse(q), 10).TotalHits;

        return new SearchResult(Rounds * Queries.Length, total, sw.Elapsed.TotalMilliseconds);
    }

    public void Dispose()
    {
        _searcher?.IndexReader.Dispose();
        _fsDir.Dispose();
        _analyzer.Dispose();
        if (System.IO.Directory.Exists(_indexDir))
            System.IO.Directory.Delete(_indexDir, recursive: true);
    }
}
