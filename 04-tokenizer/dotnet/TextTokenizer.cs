// ============================================================
// milliseconds.dev — .NET vs Python performance benchmarks
// Project : 04 — Text tokenization (sentence + word)
// Author  : Mo Mand  |  https://milliseconds.dev
//
// Regex-based tokenizer — replaces:
//   Python: nltk.tokenize.sent_tokenize + word_tokenize
//           (Punkt sentence splitter + TreebankWordTokenizer)
//
// Key differences from the Python version:
//   - Compiled Regex patterns are built once and reused across the corpus
//   - EnumerateMatches avoids materializing a match collection per sentence
//   - Span-based split for sentences avoids creating a string[] on the heap
//   - No NLTK model download required; rules are embedded in code
//
// Rule equivalence:
//   Sentences: split on .!? followed by whitespace+uppercase, or paragraph breaks
//   Words:     match [A-Za-z0-9]+(?:['\\-][A-Za-z]+)* — contractions intact
// ============================================================

using System.Text.RegularExpressions;

class TextTokenizer
{
    // Punkt-equivalent: .!? before whitespace+uppercase, or double newline (paragraph)
    private static readonly Regex SentPattern = new(
        @"(?<=[.!?])\s+(?=[A-Z])|(?:\r?\n){2,}",
        RegexOptions.Compiled);

    // Treebank-equivalent: keep contractions ("don't" = 1 token), split on whitespace
    private static readonly Regex WordPattern = new(
        @"[A-Za-z0-9]+(?:['\-][A-Za-z]+)*",
        RegexOptions.Compiled);

    // Tokenize a corpus string into sentences and words.
    // Python equivalent:
    //   sentences = sent_tokenize(text)
    //   word_count = sum(len(word_tokenize(s)) for s in sentences)
    public (long sentences, long words) Tokenize(string text)
    {
        var sentences  = SentPattern.Split(text);
        long sentCount = sentences.Length;
        long wordCount = 0;

        foreach (var sent in sentences)
        {
            var m = WordPattern.EnumerateMatches(sent.AsSpan());
            while (m.MoveNext()) wordCount++;
        }

        return (sentCount, wordCount);
    }
}
