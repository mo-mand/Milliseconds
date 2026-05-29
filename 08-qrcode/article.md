---
title: "qrcode vs QRCoder: Generating 50,000 QR Codes"
description: "Python's qrcode library generates QR codes through a pure-Python Reed-Solomon encoder. QRCoder in .NET compiles the same error correction math to native code — 14× faster at 50,000 codes."
publishedAt: "2026-05-26"
project: "08"
pythonLib: "qrcode"
dotnetLib: "QRCoder"
speedup_10k: 9.0
speedup_max: 14.0
draft: false
---

## Overview

QR code generation is a batch workload in many systems: product labels, event ticketing, URL shorteners, and payment systems all generate large volumes on demand. The encoding algorithm is fixed by the ISO 18004 standard — both `qrcode` (Python) and `QRCoder` (.NET) implement identical Reed-Solomon error correction and matrix placement.

Since the algorithm is standardized, this benchmark directly measures how much of the runtime is language overhead versus actual QR encoding work.

## Benchmark Setup

50,000 QR codes generated from random 12-character alphanumeric strings:
- Error correction level M (15% recovery capacity)
- Version auto-selected (typically version 3–4 for 12-char payloads)
- Output: dark-module count and matrix size (no image rendering — pure encoding)

Tested at 1,000 / 10,000 / 50,000 codes. Python uses `qrcode.QRCode(error_correction=ERROR_CORRECT_M, border=0)`. .NET uses `QRCoder.QRCodeGenerator` with `ECCLevel.M`.

## Results

| Codes | Python (qrcode) | .NET (QRCoder) | Speedup |
|---|---|---|---|
| 1,000 | ~0.6 s | ~95 ms | **6.3×** |
| 10,000 | ~5.9 s | ~650 ms | **9.1×** |
| 50,000 | ~29 s | ~2.1 s | **13.8×** |

## Why QRCoder Is Faster

QR encoding involves three expensive steps:

1. **Data encoding** — convert input bytes to QR codewords using mode selection and character set tables
2. **Reed-Solomon error correction** — polynomial multiplication in GF(256), repeated for every block
3. **Matrix placement** — fill the QR matrix with function patterns, data bits, and masking

In Python, each step iterates over lists of integers with per-iteration interpreter overhead. The GF(256) multiplication table lookup is a Python dict access. In .NET, all three steps compile to tight loops over `int[]` arrays with no boxing, no dict hashing, and no object allocation per symbol.

The `border=0` / `QuietZone=4` setting also matters: Python's default rendering calculates quiet zone positions in Python; the .NET implementation handles this in a single matrix-copy operation.

## Key Code

```csharp
// QRCoder — generate and count dark modules
// Replaces: qrcode.QRCode(error_correction=ERROR_CORRECT_M, border=0)
public Result Analyze(string text)
{
    using var qrGenerator = new QRCodeGenerator();
    using var data = qrGenerator.CreateQrCode(text, QRCodeGenerator.ECCLevel.M);
    var matrix = data.ModuleMatrix;
    long dark = 0;
    for (int r = 0; r < matrix.Count; r++)
        for (int c = 0; c < matrix[r].Count; c++)
            if (matrix[r][c]) dark++;
    return new Result(dark, matrix.Count);
}
```

```python
# qrcode — pure Python Reed-Solomon + matrix placement
qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, border=0)
for text in batch:
    qr.clear()
    qr.add_data(text)
    qr.make(fit=True)
    matrix = qr.get_matrix()
    dark   = sum(1 for row in matrix for cell in row if cell)
```

Both produce identical matrices. The .NET version's Reed-Solomon polynomial arithmetic runs as compiled native code rather than Python bytecode.

## Diagrams

![QR code generation time by batch size — Python grows steeply, .NET stays nearly flat](/projects/08-qrcode/Diagram1.png)

At 1,000 codes Python is ~6× slower. At 50,000 codes it's nearly 14×. The growing gap shows that per-code overhead (GF(256) table lookups, list operations) accumulates faster than any fixed startup cost.

![Throughput in codes per second — QRCoder generates ~24k codes/s vs Python's ~1,700 codes/s](/projects/08-qrcode/Diagram2.png)

For a ticketing platform generating 100,000 QR codes on demand: Python takes ~59 seconds, .NET takes ~4 seconds. The difference determines whether this can be a synchronous API call or requires a queue.
