---
title: "pypdf vs PdfPig: Text Extraction at Scale"
description: "pypdf is a pure-Python PDF parser — every byte of every page goes through the CPython interpreter. PdfPig is a pure C# equivalent. Same algorithm, same data, 4–6× faster."
publishedAt: "2026-05-22"
project: "03"
pythonLib: "pypdf"
dotnetLib: "PdfPig"
speedup_10k: 4.0
speedup_max: 6.2
draft: false
---

## Overview

PDF text extraction is a common pre-processing step in data pipelines — ingesting research papers, legal documents, or reports before embedding or indexing. Both `pypdf` and `PdfPig` are pure managed-code parsers: no native binaries, no OCR, no system PDF renderer. They implement the same PDF specification operations in their respective languages.

This makes the benchmark unusually clean: the performance difference is entirely due to language execution speed, not library architecture differences.

## Benchmark Setup

200 recent arXiv PDFs (mixed technical papers, 5–40 pages each). Tested on subsets of 10, 50, 100, and 200 files. Both libraries extract all text from all pages; output is validated for page-count agreement and character-count agreement within 15% (pypdf and PdfPig decode whitespace and encoding tables slightly differently).

## Results

| PDFs | Pages | Python (pypdf) | .NET (PdfPig) | Speedup |
|---|---|---|---|---|
| 10 | ~120 | ~0.9 s | ~230 ms | **3.9×** |
| 50 | ~600 | ~4.2 s | ~810 ms | **5.2×** |
| 100 | ~1,200 | ~8.5 s | ~1.4 s | **6.1×** |
| 200 | ~2,400 | ~17 s | ~2.7 s | **6.2×** |

The speedup grows slightly with corpus size, suggesting pypdf has a per-document startup cost that compounds as PdfPig's JIT gets warmer.

## Why PdfPig Is Faster

PDF parsing is byte-heavy: every page is a stream of PostScript-like operators (move, show text, set font, etc.). Each operator must be lexed, looked up in a dispatch table, and executed against a graphics state machine.

In Python, each operator dispatch is a Python method call — the CPython bytecode interpreter has overhead per call regardless of what the method does. In .NET, the JIT compiles the dispatch loop to native code the first time it runs; subsequent pages pay only the cost of the actual work.

Additionally, PdfPig's content-stream parser operates on `ReadOnlySpan<byte>` — zero-copy slicing through the raw page bytes with no intermediate string allocations. pypdf builds Python string objects for each token.

## Key Code

```csharp
// PdfPig — zero-copy span-based page extraction
public Result Extract(string path)
{
    using var doc = PdfDocument.Open(path);
    long chars = 0;
    foreach (var page in doc.GetPages())
        chars += page.Text.Length;
    return new Result(chars, doc.NumberOfPages, Ok: true);
}
```

```python
# pypdf — Python object per token
reader = pypdf.PdfReader(path)
chars  = 0
for page in reader.pages:
    chars += len(page.extract_text() or "")
```

The structure is identical. The performance difference is pure language execution speed on the same PDF parsing logic.

## Diagrams

![PDF extraction time by corpus size — PdfPig stays nearly linear while pypdf steepens](/projects/03-pdf-extract/Diagram1.png)

Both scale linearly in page count, but PdfPig's slope is 6× shallower. At 200 files (a typical daily batch job), .NET finishes in under 3 seconds; Python takes 17 seconds.

![Speedup multiplier by subset size — gap widens as JIT warms up](/projects/03-pdf-extract/Diagram2.png)

The 10-file speedup (3.9×) is lower because .NET's JIT incurs one-time compilation overhead for the PDF parser code paths. By 50 files the JIT is fully warm and the speedup stabilises around 6×.
