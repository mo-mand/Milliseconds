"""
Date parsing benchmark: Python (python-dateutil) vs .NET 10 (DateTime.TryParseExact).

Runs on 100k, 500k, and 1M date strings across 8 common formats.
Validates that the checksum (sum of YYYYMMDD integers for all parsed dates)
is byte-identical between runtimes.

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
DOTNET_PROJ = ROOT / "dotnet" / "DateParse.csproj"
PYTHON      = sys.executable
BENCH       = Path(__file__).parent / "parse_dates.py"

DATASETS = [
    ("100k", DATA_DIR / "dates_100k.txt"),
    ("500k", DATA_DIR / "dates_500k.txt"),
    ("1M",   DATA_DIR / "dates_1m.txt"),
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
    if py["dates"] != cs["dates"]:
        issues.append(f"date count mismatch: Python={py['dates']:,} .NET={cs['dates']:,}")
    if py["checksum"] != cs["checksum"]:
        issues.append(f"checksum mismatch: Python={py['checksum']:,} .NET={cs['checksum']:,}")
    if py["failed"] > 0 or cs["failed"] > 0:
        issues.append(f"parse failures: Python={py['failed']:,} .NET={cs['failed']:,}")
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
        print(f"Skipping {label} -- file not found. Run build_dates.py first.")
        continue

    print(f"{'='*55}")
    print(f"Dataset: {label} dates  ({path.stat().st_size // 1024:,} KB)")

    print("  Running Python (dateutil) ...")
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
        "label":    label,
        "dates":    py.get("dates", cs.get("dates", 0)),
        "checksum": py.get("checksum", 0),
        "py_ms":    py.get("elapsed_ms", 0),
        "cs_ms":    cs.get("elapsed_ms", 0),
        "status":   status,
    })

# ---- Table ------------------------------------------------------------------
print()
print("=" * 75)
print(f"{'Dates':<8} {'Checksum':>18} {'Python':>12} {'.NET':>10} {'Speedup':>10} {'Valid':>6}")
print("-" * 75)
for r in rows:
    sx = speedup(r["py_ms"], r["cs_ms"]) if r["py_ms"] and r["cs_ms"] else "N/A"
    print(f"{r['label']:<8} {r['checksum']:>18,} {fmt(r['py_ms']):>12}"
          f" {fmt(r['cs_ms']):>10} {sx:>10} {r['status']:>6}")
print("=" * 75)
print()
print("Checksum = sum of YYYYMMDD integers for every parsed date.")
print("Formats: ISO 8601, RFC 2822, long/short US, day-month, slash, HH:MM variants.")
