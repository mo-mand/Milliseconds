"""
PDF extraction benchmark: Python (pypdf) vs .NET 10 (PdfPig).

Runs on subsets of increasing size to show how performance scales.
Validates that page counts and character counts agree within tolerance.

Usage:
    python benchmark_all.py
"""

import sys
import json
import subprocess
import shutil
import time
from pathlib import Path

ROOT     = Path(__file__).parent.parent
PDF_DIR  = ROOT / "data" / "pdfs"
DOTNET   = r"C:\Codex\Milliseconds\.dotnet\dotnet.exe"
DOTNET_PROJ = ROOT / "dotnet" / "PdfExtract.csproj"
PYTHON   = sys.executable
EXTRACT  = Path(__file__).parent / "extract.py"

SUBSETS = [10, 50, 100, 200]      # number of PDFs per run

# ---------------------------------------------------------------------------
def run(cmd: list[str], timeout=600) -> dict:
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if result.returncode != 0:
        raise RuntimeError(result.stderr[:500])
    return json.loads(result.stdout.strip())

def fmt_ms(ms: float) -> str:
    if ms >= 60_000: return f"{ms/60_000:.1f} min"
    if ms >= 1_000:  return f"{ms/1_000:.2f} s"
    return f"{ms:.0f} ms"

def speedup(py_ms: float, cs_ms: float) -> str:
    return f"{py_ms / cs_ms:.1f}x"

def validate(py: dict, cs: dict) -> tuple[bool, list[str]]:
    issues = []
    if py["files"] != cs["files"]:
        issues.append(f"file count mismatch: Python={py['files']} .NET={cs['files']}")
    if py["pages"] != cs["pages"]:
        issues.append(f"page count mismatch: Python={py['pages']} .NET={cs['pages']}")
    # Character counts differ because pypdf and PdfPig handle whitespace/encoding
    # slightly differently — allow 15% relative tolerance.
    rel = abs(py["chars"] - cs["chars"]) / max(py["chars"], 1)
    if rel > 0.15:
        issues.append(f"char count diverges by {rel:.1%}: Python={py['chars']:,} .NET={cs['chars']:,}")
    return len(issues) == 0, issues

# ---------------------------------------------------------------------------
# Build .NET
# ---------------------------------------------------------------------------
print("Building .NET project ...")
r = subprocess.run(
    [DOTNET, "build", str(DOTNET_PROJ), "-c", "Release", "--nologo", "-v", "q"],
    capture_output=True, text=True
)
if r.returncode != 0:
    sys.exit(f"Build failed:\n{r.stderr}")
print("Build OK\n")

# ---------------------------------------------------------------------------
# Check data
# ---------------------------------------------------------------------------
all_pdfs = sorted(PDF_DIR.glob("*.pdf"))
if len(all_pdfs) < max(SUBSETS):
    print(f"Only {len(all_pdfs)} PDFs found (need {max(SUBSETS)}). Running download ...")
    subprocess.run([PYTHON, str(Path(__file__).parent / "download_data.py"),
                    "--count", str(max(SUBSETS))], check=True)
    all_pdfs = sorted(PDF_DIR.glob("*.pdf"))

# ---------------------------------------------------------------------------
# For each subset size: create a temp dir with N PDFs, run both
# ---------------------------------------------------------------------------
rows = []
TEMP = ROOT / "data" / "_bench_tmp"

for n in SUBSETS:
    if n > len(all_pdfs):
        print(f"Skipping subset {n} — not enough PDFs")
        continue

    subset = all_pdfs[:n]
    TEMP.mkdir(exist_ok=True)

    # Populate temp dir with symlinks (or copies on Windows).
    for f in TEMP.glob("*.pdf"): f.unlink()
    for f in subset:
        shutil.copy2(f, TEMP / f.name)

    print(f"{'='*55}")
    print(f"Subset: {n} PDFs")

    print(f"  Running Python (pypdf) ...")
    try:
        py = run([PYTHON, str(EXTRACT), str(TEMP), "--json"])
        py_ok = True
    except Exception as e:
        print(f"  Python FAILED: {e}"); py_ok = False; py = {}

    print(f"  Running .NET (PdfPig) ...")
    try:
        cs = run([DOTNET, "run", "-c", "Release", "--no-build",
                  "--project", str(DOTNET_PROJ), str(TEMP), "--json"])
        cs_ok = True
    except Exception as e:
        print(f"  .NET FAILED: {e}"); cs_ok = False; cs = {}

    status = "ERROR"
    if py_ok and cs_ok:
        valid, issues = validate(py, cs)
        status = "PASS" if valid else "FAIL"
        for iss in issues: print(f"  VALIDATION: {iss}")
        print(f"  Python: {fmt_ms(py['elapsed_ms'])}   "
              f".NET: {fmt_ms(cs['elapsed_ms'])}   "
              f"Speedup: {speedup(py['elapsed_ms'], cs['elapsed_ms'])}   [{status}]")

    rows.append({
        "n":       n,
        "pages":   py.get("pages", cs.get("pages", 0)),
        "py_ms":   py.get("elapsed_ms", 0),
        "cs_ms":   cs.get("elapsed_ms", 0),
        "py_err":  py.get("errors", 0),
        "cs_err":  cs.get("errors", 0),
        "status":  status,
    })

# Cleanup temp dir
shutil.rmtree(TEMP, ignore_errors=True)

# ---------------------------------------------------------------------------
# Summary table
# ---------------------------------------------------------------------------
print()
print("=" * 80)
print(f"{'PDFs':>6} {'Pages':>8} {'Py time':>12} {'CS time':>12} {'Speedup':>10} {'Valid':>6}")
print("-" * 80)
for r in rows:
    sx = speedup(r["py_ms"], r["cs_ms"]) if r["py_ms"] and r["cs_ms"] else "N/A"
    print(f"{r['n']:>6} {r['pages']:>8,} {fmt_ms(r['py_ms']):>12} "
          f"{fmt_ms(r['cs_ms']):>12} {sx:>10} {r['status']:>6}")
print("=" * 80)
print()
print("Valid = page counts match; char counts within 15% (pypdf/PdfPig encode whitespace differently)")
