"""
Markdown rendering benchmark - pure Python, mistune.

Uses mistune 3.x with default HTML renderer (zero C extensions).

Usage:
    python render.py [path/to/docs.txt] [--json]
"""

import sys
import json
import time
from pathlib import Path

try:
    import mistune
except ImportError:
    sys.exit("mistune not installed. Run: pip install mistune")

JSON_MODE = "--json" in sys.argv
path_args = [a for a in sys.argv[1:] if not a.startswith("--")]

docs_path = Path(path_args[0]) if path_args else \
            Path(__file__).parent.parent / "data" / "docs_10k.txt"

if not docs_path.exists():
    sys.exit(f"File not found: {docs_path}\nRun: python build_corpus.py")

def log(msg):
    if not JSON_MODE:
        print(msg, flush=True)

md = mistune.create_markdown()

log(f"Loading docs from: {docs_path}")
lines = docs_path.read_text(encoding="utf-8").splitlines()
log(f"Docs: {len(lines):,}")

t0 = time.perf_counter()
total_html_chars = 0

for line in lines:
    if not line.strip():
        continue
    html = md(line)
    total_html_chars += len(html)

elapsed_ms = (time.perf_counter() - t0) * 1000

if JSON_MODE:
    print(json.dumps({
        "docs":       len(lines),
        "html_chars": total_html_chars,
        "elapsed_ms": round(elapsed_ms, 1),
    }))
else:
    print(f"\nHTML chars : {total_html_chars:,}")
    print(f"Elapsed    : {elapsed_ms:.1f} ms")
    print(f"Throughput : {len(lines) / (elapsed_ms / 1000):.0f} docs/s")
