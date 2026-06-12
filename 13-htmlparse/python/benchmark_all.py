"""
HTML parsing benchmark: Python (BeautifulSoup4 + html.parser) vs .NET 10 (AngleSharp).

Per document: parse HTML -> find all <a> hrefs -> count <td> cells -> extract <h1> text.
Validates that href and td counts match exactly between runtimes.

Usage:
    python benchmark_all.py
"""

import sys, json, subprocess
from pathlib import Path

ROOT        = Path(__file__).parent.parent
DATA_DIR    = ROOT / "data"
DOTNET      = r"C:\Program Files\dotnet\dotnet.exe"
DOTNET_PROJ = ROOT / "dotnet" / "HtmlParse.csproj"
PYTHON      = sys.executable
BENCH       = Path(__file__).parent / "parse.py"

DATASETS = [
    ("5k",  DATA_DIR / "docs_5k"),
    ("20k", DATA_DIR / "docs_20k"),
    ("50k", DATA_DIR / "docs_50k"),
]


def run(cmd, timeout=3600):
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError(r.stderr[:600])
    return json.loads(r.stdout.strip())


def fmt(ms):
    if ms >= 60_000: return f"{ms / 60_000:.2f} min"
    if ms >= 1_000:  return f"{ms / 1_000:.2f} s"
    return f"{ms:.0f} ms"


def speedup(py, cs):
    return f"{py / cs:.1f}x"


def validate(py, cs):
    issues = []
    if py["docs"] != cs["docs"]:
        issues.append(f"doc count mismatch: {py['docs']} vs {cs['docs']}")
    if py["total_hrefs"] != cs["total_hrefs"]:
        issues.append(f"href count mismatch: Python={py['total_hrefs']:,} .NET={cs['total_hrefs']:,}")
    if py["total_tds"] != cs["total_tds"]:
        issues.append(f"td count mismatch: Python={py['total_tds']:,} .NET={cs['total_tds']:,}")
    return len(issues) == 0, issues


# ---- Build ------------------------------------------------------------------
print("Building .NET project ...")
r = subprocess.run(
    [DOTNET, "build", str(DOTNET_PROJ), "-c", "Release", "--nologo", "-v", "q"],
    capture_output=True, text=True,
)
if r.returncode != 0:
    sys.exit(f"Build failed:\n{r.stderr}")
print("Build OK\n")

# ---- Run --------------------------------------------------------------------
rows = []
for label, path in DATASETS:
    if not path.exists() or not any(path.glob("*.html")):
        print(f"Skipping {label} -- run build_inputs.py first.")
        continue

    count = len(list(path.glob("*.html")))
    print(f"{'=' * 55}")
    print(f"Dataset: {label}  ({count:,} documents)")

    print("  Running Python (BeautifulSoup4) ...")
    try:
        py = run([PYTHON, str(BENCH), str(path), "--json"])
        py_ok = True
    except Exception as e:
        print(f"  Python FAILED: {e}"); py_ok = False; py = {}

    print("  Running .NET (AngleSharp) ...")
    try:
        cs = run([DOTNET, "run", "-c", "Release", "--no-build",
                  "--project", str(DOTNET_PROJ), "--", str(path), "--json"])
        cs_ok = True
    except Exception as e:
        print(f"  .NET FAILED: {e}"); cs_ok = False; cs = {}

    status = "ERROR"
    if py_ok and cs_ok:
        valid, issues = validate(py, cs)
        status = "PASS" if valid else "WARN"
        for iss in issues:
            print(f"  VALIDATION: {iss}")
        sx = speedup(py["elapsed_ms"], cs["elapsed_ms"])
        print(f"  Python: {fmt(py['elapsed_ms'])}   .NET: {fmt(cs['elapsed_ms'])}"
              f"   Speedup: {sx}   [{status}]")

    rows.append({
        "label":  label,
        "py_ms":  py.get("elapsed_ms", 0),
        "cs_ms":  cs.get("elapsed_ms", 0),
        "status": status,
    })

# ---- Summary ----------------------------------------------------------------
print()
print("=" * 60)
print(f"{'Docs':<8} {'Python':>12} {'.NET':>10} {'Speedup':>10} {'Valid':>6}")
print("-" * 60)
for r in rows:
    sx = speedup(r["py_ms"], r["cs_ms"]) if r["py_ms"] and r["cs_ms"] else "N/A"
    print(f"{r['label']:<8} {fmt(r['py_ms']):>12} {fmt(r['cs_ms']):>10} {sx:>10} {r['status']:>6}")
print("=" * 60)
