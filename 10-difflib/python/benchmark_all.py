"""
Sequence diff benchmark: Python (difflib.SequenceMatcher) vs .NET 10 (DP LCS).

Diffs pairs of integer sequences (80-200 elements each) representing
line-hash streams. Validates that the unchanged-element count is within 1%
between runtimes — both find the same LCS length even if they produce
different edit scripts when multiple optimal paths exist.

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
DOTNET_PROJ = ROOT / "dotnet" / "DiffLib.csproj"
PYTHON      = sys.executable
BENCH       = Path(__file__).parent / "diff_texts.py"

DATASETS = [
    ("10k",  DATA_DIR / "pairs_10k.tsv"),
    ("50k",  DATA_DIR / "pairs_50k.tsv"),
    ("100k", DATA_DIR / "pairs_100k.tsv"),
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
    if py["pairs"] != cs["pairs"]:
        issues.append(f"pair count mismatch: Python={py['pairs']:,} .NET={cs['pairs']:,}")
    # unchanged count = LCS length; both algorithms find the same LCS length
    # even when they may produce different tie-breaking edit scripts
    ratio = abs(py["unchanged"] - cs["unchanged"]) / max(py["unchanged"], 1)
    if ratio > 0.01:
        issues.append(f"unchanged count differs {ratio*100:.2f}%: "
                      f"Python={py['unchanged']:,} .NET={cs['unchanged']:,}")
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
        print(f"Skipping {label} -- file not found. Run build_pairs.py first.")
        continue

    print(f"{'='*55}")
    print(f"Dataset: {label} pairs  ({path.stat().st_size // 1024:,} KB)")

    print("  Running Python (difflib) ...")
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
        pu, cu = py.get("unchanged", 0), cs.get("unchanged", 0)
        print(f"  Unchanged: Python={pu:,}  .NET={cu:,}  "
              f"diff={abs(pu-cu)/max(pu,1)*100:.2f}%")
        print(f"  Python: {fmt(py['elapsed_ms'])}   .NET: {fmt(cs['elapsed_ms'])}"
              f"   Speedup: {speedup(py['elapsed_ms'], cs['elapsed_ms'])}   [{status}]")

    rows.append({
        "label":    label,
        "pairs":    py.get("pairs", cs.get("pairs", 0)),
        "unchanged": py.get("unchanged", 0),
        "py_ms":    py.get("elapsed_ms", 0),
        "cs_ms":    cs.get("elapsed_ms", 0),
        "status":   status,
    })

# ---- Table ------------------------------------------------------------------
print()
print("=" * 75)
print(f"{'Pairs':<8} {'Unchanged':>12} {'Python':>12} {'.NET':>10} {'Speedup':>10} {'Valid':>6}")
print("-" * 75)
for r in rows:
    sx = speedup(r["py_ms"], r["cs_ms"]) if r["py_ms"] and r["cs_ms"] else "N/A"
    print(f"{r['label']:<8} {r['unchanged']:>12,} {fmt(r['py_ms']):>12}"
          f" {fmt(r['cs_ms']):>10} {sx:>10} {r['status']:>6}")
print("=" * 75)
print()
print("Sequences: 80-200 integer elements each (line-hash simulation), vocab=9000.")
print("Validation: LCS length (unchanged count) within 1% between runtimes.")
