// ============================================================
// milliseconds.dev — .NET vs Python performance benchmarks
// Project : 03 — PDF text extraction
// Author  : Mo Mand  |  https://milliseconds.dev
//
// PdfPig-based text extractor — replaces:
//   Python: PyMuPDF (fitz) — page.get_text()
//
// Key differences from the Python version:
//   - PdfPig is 100% managed C# — no native libmupdf shared library
//   - StringBuilder is pre-allocated and cleared per page (not per word)
//     to avoid string concatenation churn
//   - Errors are caught per file so the benchmark continues on corrupt PDFs
// ============================================================

using System.Text;
using UglyToad.PdfPig;
using UglyToad.PdfPig.Content;

class PdfExtractor
{
    private readonly StringBuilder _sb = new StringBuilder(4096);

    public readonly record struct Result(long Chars, long Pages, bool Ok);

    // Extract all text from a single PDF file.
    // Python equivalent:
    //   doc = fitz.open(path)
    //   for page in doc:
    //       text = page.get_text()
    //       total_chars += len(text)
    public Result Extract(string path)
    {
        try
        {
            long chars = 0;
            long pages = 0;
            using var doc = PdfDocument.Open(path);
            foreach (Page page in doc.GetPages())
            {
                _sb.Clear();
                foreach (var word in page.GetWords())
                    _sb.Append(word.Text).Append(' ');
                chars += _sb.Length;
                pages++;
            }
            return new Result(chars, pages, Ok: true);
        }
        catch
        {
            return new Result(0, 0, Ok: false);
        }
    }
}
