"""
PDF text extraction — pure Python, pypdf (zero C extensions).

Extracts all text from every PDF in a directory, counts total chars/pages.

Usage:
    python extract.py [path/to/pdf/dir] [--json]
"""

import sys
import json
import time
from pathlib import Path

try:
    import pypdf
except ImportError:
    sys.exit("pypdf not installed. Run: pip install pypdf")

JSON_MODE = "--json" in sys.argv
path_args = [a for a in sys.argv[1:] if not a.startswith("--")]

pdf_dir = Path(path_args[0]) if path_args else Path(__file__).parent.parent / "data" / "pdfs"

if not pdf_dir.exists():
    sys.exit(f"Directory not found: {pdf_dir}\nRun: python download_data.py")

files = sorted(pdf_dir.glob("*.pdf"))
if not files:
    sys.exit(f"No PDF files found in {pdf_dir}")

def log(msg):
    if not JSON_MODE:
        print(msg, flush=True)

log(f"Extracting text from {len(files)} PDFs in: {pdf_dir}")

t0 = time.perf_counter()

total_chars = 0
total_pages = 0
errors      = 0

for path in files:
    try:
        reader = pypdf.PdfReader(str(path), strict=False)
        for page in reader.pages:
            text = page.extract_text() or ""
            total_chars += len(text)
            total_pages += 1
    except Exception:
        errors += 1

elapsed_ms = (time.perf_counter() - t0) * 1000

if JSON_MODE:
    print(json.dumps({
        "files":      len(files),
        "pages":      total_pages,
        "chars":      total_chars,
        "errors":     errors,
        "elapsed_ms": round(elapsed_ms, 1),
    }))
else:
    print(f"\nFiles   : {len(files)}")
    print(f"Pages   : {total_pages:,}")
    print(f"Chars   : {total_chars:,}")
    print(f"Errors  : {errors}")
    print(f"Elapsed : {elapsed_ms:.1f} ms  ({elapsed_ms / len(files):.1f} ms/file)")
