"""
Search benchmark: Python (Whoosh) vs .NET 10 (Lucene.NET).

Runs on 10k, 50k, and 100k document corpora.
Validates that search hit counts are within 5% tolerance
(Whoosh and Lucene use the same TF-IDF logic but differ in
minor scoring details, so exact hit counts may vary slightly).

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
DOTNET_PROJ = ROOT / "dotnet" / "WhooshNet.csproj"
PYTHON      = sys.executable
BENCH       = Path(__file__).parent / "index_search.py"

CORPORA = [
    ("10k",  DATA_DIR / "docs_10k.jsonl"),
    ("50k",  DATA_DIR / "docs_50k.jsonl"),
    ("100k", DATA_DIR / "docs_100k.jsonl"),
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
    if py["total_queries"] != cs["total_queries"]:
        issues.append(f"query count mismatch")
    rel = abs(py["total_hits"] - cs["total_hits"]) / max(py["total_hits"], 1)
    if rel > 0.05:
        issues.append(f"hit count off by {rel:.1%}: Python={py['total_hits']:,} .NET={cs['total_hits']:,}")
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
for label, path in CORPORA:
    if not path.exists():
        print(f"Skipping {label} — file not found. Run build_corpus.py first.")
        continue

    size_mb = path.stat().st_size / 1_048_576
    print(f"{'='*55}")
    print(f"Corpus: {label}  ({size_mb:.1f} MB)")

    print("  Running Python (Whoosh) ...")
    try:
        py = run([PYTHON, str(BENCH), str(path), "--json"])
        py_ok = True
    except Exception as e:
        print(f"  Python FAILED: {e}"); py_ok = False; py = {}

    print("  Running .NET (Lucene.NET) ...")
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
        print(f"  Index  — Python: {fmt(py['index_ms'])}   .NET: {fmt(cs['index_ms'])}   "
              f"Speedup: {speedup(py['index_ms'], cs['index_ms'])}")
        print(f"  Search — Python: {fmt(py['search_ms'])}   .NET: {fmt(cs['search_ms'])}   "
              f"Speedup: {speedup(py['search_ms'], cs['search_ms'])}   [{status}]")

    rows.append({
        "label":       label,
        "docs":        py.get("docs", cs.get("docs", 0)),
        "py_idx":      py.get("index_ms", 0),
        "cs_idx":      cs.get("index_ms", 0),
        "py_srch":     py.get("search_ms", 0),
        "cs_srch":     cs.get("search_ms", 0),
        "py_hits":     py.get("total_hits", 0),
        "cs_hits":     cs.get("total_hits", 0),
        "status":      status,
    })

# ---- Table ------------------------------------------------------------------
print()
print("=" * 95)
print(f"{'Docs':<8} {'Py Index':>10} {'CS Index':>10} {'Idx Spdup':>10}"
      f" {'Py Search':>10} {'CS Search':>10} {'Srch Spdup':>11} {'Valid':>6}")
print("-" * 95)
for r in rows:
    ix = speedup(r['py_idx'],  r['cs_idx'])  if r['py_idx']  and r['cs_idx']  else "N/A"
    sx = speedup(r['py_srch'], r['cs_srch']) if r['py_srch'] and r['cs_srch'] else "N/A"
    print(f"{r['label']:<8} {fmt(r['py_idx']):>10} {fmt(r['cs_idx']):>10} {ix:>10}"
          f" {fmt(r['py_srch']):>10} {fmt(r['cs_srch']):>10} {sx:>11} {r['status']:>6}")
print("=" * 95)
print()
print("1 000 queries per run (50 rounds x 20 terms) against a fresh in-memory+disk Lucene/Whoosh index.")
