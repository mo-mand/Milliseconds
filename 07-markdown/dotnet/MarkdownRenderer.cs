// ============================================================
// milliseconds.dev — .NET vs Python performance benchmarks
// Project : 07 — Markdown rendering
// Author  : Mo Mand  |  https://milliseconds.dev
//
// Markdig-based Markdown renderer — replaces:
//   Python: mistune.create_markdown()  (mistune 3.x)
//
// Key differences from the Python version:
//   - Single MarkdownPipeline instance reused across all documents
//     (thread-safe by design); mistune creates a new renderer per call
//   - No advanced extensions (heading IDs, attribute lists) — matches
//     mistune's default output exactly for checksum validation
//   - Markdig processes entirely in managed C# with no Python object overhead
// ============================================================

using Markdig;

class MarkdownRenderer
{
    // Build the pipeline once — equivalent to mistune.create_markdown()
    // No UseAdvancedExtensions: keeps output compatible with mistune defaults.
    private readonly MarkdownPipeline _pipeline = new MarkdownPipelineBuilder().Build();

    // Render a single Markdown string to HTML.
    // Python equivalent: html = md(doc)
    public string Render(string markdown) => Markdown.ToHtml(markdown, _pipeline);
}
