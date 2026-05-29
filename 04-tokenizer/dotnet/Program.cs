// ============================================================
// milliseconds.dev — .NET vs Python performance benchmarks
// Project : 04 — Text tokenization (sentence + word)
// Author  : Mo Mand  |  https://milliseconds.dev
//
// CLI harness: parse args, load corpus, run the benchmark,
// emit JSON or human-readable results.
// Python equivalent: python/tokenize_text.py
// ============================================================

using System.Diagnostics;
using System.Text.Json;

bool jsonMode = args.Contains("--json");
var  pathArgs = args.Where(a => !a.StartsWith("--")).ToArray();

var textPath = pathArgs.Length > 0 ? pathArgs[0]
    : Path.Combine(AppContext.BaseDirectory, "..", "..", "..", "..", "data", "corpus.txt");

if (!File.Exists(textPath))
{
    Console.Error.WriteLine($"File not found: {textPath}");
    Console.Error.WriteLine("Run: python python/download_data.py");
    return 1;
}

void Log(string msg) { if (!jsonMode) Console.WriteLine(msg); }

Log($"Reading: {textPath}");
var t0 = Stopwatch.GetTimestamp();
string text = File.ReadAllText(textPath);
double loadMs = Stopwatch.GetElapsedTime(t0).TotalMilliseconds;
Log($"Size: {text.Length:N0} chars  (loaded in {loadMs:F0} ms)");

// TextTokenizer wraps compiled Regex patterns matching NLTK's Punkt + Treebank rules.
// See TextTokenizer.cs for pattern details.
var tokenizer = new TextTokenizer();

Log("Tokenizing ...");
var sw = Stopwatch.StartNew();

// Python equivalent:
//   from nltk.tokenize import sent_tokenize, word_tokenize
//   sentences = sent_tokenize(text)
//   words = [w for s in sentences for w in word_tokenize(s)]
var (sentCount, wordCount) = tokenizer.Tokenize(text);

sw.Stop();
double computeMs = sw.Elapsed.TotalMilliseconds;

if (jsonMode)
{
    Console.WriteLine(JsonSerializer.Serialize(new
    {
        chars      = (long)text.Length,
        sentences  = sentCount,
        words      = wordCount,
        load_ms    = Math.Round(loadMs, 1),
        compute_ms = Math.Round(computeMs, 1),
    }));
}
else
{
    Log($"\nSentences : {sentCount:N0}");
    Log($"Words     : {wordCount:N0}");
    Log($"Elapsed   : {computeMs:F1} ms");
    Log($"Throughput: {text.Length / (computeMs / 1000) / 1_000_000:F2} MB/s");
}

return 0;
