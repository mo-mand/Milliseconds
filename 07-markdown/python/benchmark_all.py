"""
Markdown rendering benchmark: Python (mistune) vs .NET 10 (Markdig).

Runs on 10k, 50k, and 100k one-line Markdown documents.
Validates that rendered HTML character counts are within 2% of each other
(mistune and Markdig may differ slightly in whitespace/tag formatting).

Usage:
    python benchmark_all.py
"""

import sys
import json
import subprocess
from pathlib import Path

ROOT        = Path(__file__).parent.parent
DATA_DIR    = ROOT / "data"
DOTNET      = r"C:\Codex\Milliseconds\.dotnet\dotnet.exe"
DOTNET_PROJ = ROOT / "dotnet" / "Markdown.csproj"
PYTHON      = sys.executable
BENCH       = Path(__file__).parent / "render.py"

DATASETS = [
    ("10k",  DATA_DIR / "docs_10k.txt"),
    ("50k",  DATA_DIR / "docs_50k.txt"),
    ("100k", DATA_DIR / "docs_100k.txt"),
]

def run(cmd, timeout=3600):
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError(r.stderr[:500])
    return json.loads(r.stdout.strip())

def fmt(ms):
    if ms >= 60_000: return f"{ms/60_000:.2f} min"
    if ms >= 1_000:  return f"{ms/1_000:.2f} s"
    return f"{ms:.0f} ms"

def speedup(py, cs):
    return f"{py/cs:.1f}x"

def validate(py, cs):
    issues = []
    if py["docs"] != cs["docs"]:
        issues.append(f"doc count mismatch: Python={py['docs']:,} .NET={cs['docs']:,}")
    # HTML char counts may differ slightly due to whitespace differences
    ratio = abs(py["html_chars"] - cs["html_chars"]) / max(py["html_chars"], 1)
    if ratio > 0.02:
        issues.append(f"html_chars differ {ratio*100:.1f}%: Python={py['html_chars']:,} .NET={cs['html_chars']:,}")
    return len(issues) == 0, issues

# ---- Build ------------------------------------------------------------------
print("Building .NET project ...")
r = subprocess.run(
    [DOTNET, "build", str(DOTNET_PROJ), "-c", "Release", "--nologo", "-v", "q"],
    capture_output=True, text=True)
if r.returncode != 0:
    sys.exit(f"Build failed:\n{r.stderr}")
print("Build OK\n")

# ---- Run --------------------------------------------------------------------
rows = []
for label, path in DATASETS:
    if not path.exists():
        print(f"Skipping {label} -- file not found. Run build_corpus.py first.")
        continue

    print(f"{'='*55}")
    print(f"Dataset: {label} docs  ({path.stat().st_size // 1024:,} KB)")

    print("  Running Python (mistune) ...")
    try:
        py = run([PYTHON, str(BENCH), str(path), "--json"])
        py_ok = True
    except Exception as e:
        print(f"  Python FAILED: {e}"); py_ok = False; py = {}

    print("  Running .NET ...")
    try:
        cs = run([DOTNET, "run", "-c", "Release", "--no-build",
                  "--project", str(DOTNET_PROJ), str(path), "--json"])
        cs_ok = True
    except Exception as e:
        print(f"  .NET FAILED: {e}"); cs_ok = False; cs = {}

    status = "ERROR"
    if py_ok and cs_ok:
        valid, issues = validate(py, cs)
        status = "PASS" if valid else "FAIL"
        for iss in issues: print(f"  VALIDATION: {iss}")
        print(f"  Python: {fmt(py['elapsed_ms'])}   .NET: {fmt(cs['elapsed_ms'])}"
              f"   Speedup: {speedup(py['elapsed_ms'], cs['elapsed_ms'])}   [{status}]")

    rows.append({
        "label":      label,
        "docs":       py.get("docs", cs.get("docs", 0)),
        "html_chars": py.get("html_chars", 0),
        "py_ms":      py.get("elapsed_ms", 0),
        "cs_ms":      cs.get("elapsed_ms", 0),
        "status":     status,
    })

# ---- Table ------------------------------------------------------------------
print()
print("=" * 75)
print(f"{'Docs':<8} {'HTML chars':>14} {'Python':>12} {'.NET':>10} {'Speedup':>10} {'Valid':>6}")
print("-" * 75)
for r in rows:
    sx = speedup(r["py_ms"], r["cs_ms"]) if r["py_ms"] and r["cs_ms"] else "N/A"
    print(f"{r['label']:<8} {r['html_chars']:>14,} {fmt(r['py_ms']):>12}"
          f" {fmt(r['cs_ms']):>10} {sx:>10} {r['status']:>6}")
print("=" * 75)
print()
print("HTML chars = total characters in rendered HTML across all docs.")
print("Validation: html_chars within 2% between runtimes.")
