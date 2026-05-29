---
title: "mistune vs Markdig: Rendering 10,000 Markdown Documents"
description: "mistune is Python's fastest Markdown parser. Markdig is .NET's equivalent. Both parse CommonMark-compatible Markdown to HTML — Markdig does it 11× faster on 10,000 real-world documents."
publishedAt: "2026-05-25"
project: "07"
pythonLib: "mistune"
dotnetLib: "Markdig"
speedup_10k: 7.0
speedup_max: 11.0
draft: false
---

## Overview

Markdown rendering shows up in documentation systems, static site generators, API responses for rich text, and content management pipelines. `mistune` is consistently benchmarked as Python's fastest Markdown parser — it uses a regex-based scanner with minimal Python object overhead. `Markdig` is .NET's most popular Markdown library, built on a character-scanner architecture with extension points for CommonMark compliance.

Both produce equivalent HTML for standard Markdown input. The benchmark isolates pure rendering throughput: no I/O, no template engine, just Markdown string in → HTML string out.

## Benchmark Setup

10,000 documents from a Wikipedia plain-text dump, converted to Markdown format:
- Mix of headings, paragraphs, bold/italic, inline code, fenced code blocks, lists, and links
- Average document: ~2,500 characters
- Total input: ~25 MB of Markdown text

Tested at 1,000 / 5,000 / 10,000 documents.

## Results

| Documents | Python (mistune) | .NET (Markdig) | Speedup |
|---|---|---|---|
| 1,000 | ~0.9 s | ~130 ms | **6.9×** |
| 5,000 | ~4.4 s | ~480 ms | **9.2×** |
| 10,000 | ~8.8 s | ~800 ms | **11×** |

## Why Markdig Is Faster

**Pipeline reuse.** `Markdig` requires building a `MarkdownPipeline` once — it's thread-safe and reused across all documents. `mistune`'s `create_markdown()` is designed to be called once per style, but the underlying renderer still allocates Python objects per document during parsing.

**Character-at-a-time scanning in native code.** Markdig's block parser and inline parser each process characters through a JIT-compiled state machine. Python's regex engine (even the fast PCRE-style one in mistune) adds interpreter overhead per match object created.

**No intermediate AST allocation.** Markdig's pipeline streams tokens directly from the scanner into the HTML writer without building a full AST in memory. mistune builds a list of (type, content) tuples as an intermediate representation.

## Key Code

```csharp
// Pipeline built once, reused for all 10,000 documents
// Python equivalent: md = mistune.create_markdown()
private readonly MarkdownPipeline _pipeline =
    new MarkdownPipelineBuilder().Build();

public string Render(string markdown) =>
    Markdown.ToHtml(markdown, _pipeline);
```

```python
# mistune — create once, call per document
md = mistune.create_markdown()
for doc in documents:
    html = md(doc)
```

The interface is nearly identical. The difference is what happens inside: `Markdown.ToHtml` dispatches to JIT-compiled C# scanning code, while `md(doc)` dispatches through Python's regex engine and object system.

## Diagrams

![Rendering time by document count — Markdig stays under 1 second for 10k documents](/projects/07-markdown/Diagram1.png)

mistune's time grows linearly with document count. Markdig's growth is also linear but with a slope roughly 11× smaller. At 10,000 documents: 8.8 seconds vs 800 milliseconds.

![Throughput in documents per second — Markdig processes ~12,500 docs/s vs mistune's ~1,130 docs/s](/projects/07-markdown/Diagram2.png)

Throughput matters for pipeline systems: a documentation site generating 100,000 pages at build time takes 88 seconds with mistune, 8 seconds with Markdig.
