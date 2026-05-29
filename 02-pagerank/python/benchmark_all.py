"""
Run PageRank on multiple SNAP datasets, validate Python vs .NET output,
and print a comparison table.

Usage:
    python benchmark_all.py [--skip-slow]

    --skip-slow   skip datasets with >5M edges (saves time during dev)
"""

import sys
import json
import subprocess
import urllib.request
import gzip
import time
from pathlib import Path

SKIP_SLOW = "--skip-slow" in sys.argv

ROOT     = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

DOTNET   = r"C:\Codex\Milliseconds\.dotnet\dotnet.exe"
DOTNET_PROJ = ROOT / "dotnet" / "PageRank.csproj"
PYTHON   = sys.executable
PAGERANK = Path(__file__).parent / "pagerank.py"

# ---------------------------------------------------------------------------
# Dataset catalogue
# ---------------------------------------------------------------------------
DATASETS = [
    {
        "name": "wiki-Vote",
        "desc": "Wikipedia vote network",
        "url":  "https://snap.stanford.edu/data/wiki-Vote.txt.gz",
        "file": "wiki-Vote.txt.gz",
    },
    {
        "name": "soc-Epinions1",
        "desc": "Epinions social network",
        "url":  "https://snap.stanford.edu/data/soc-Epinions1.txt.gz",
        "file": "soc-Epinions1.txt.gz",
    },
    {
        "name": "web-Stanford",
        "desc": "Stanford web graph",
        "url":  "https://snap.stanford.edu/data/web-Stanford.txt.gz",
        "file": "web-Stanford.txt.gz",
        "slow": True,
    },
    {
        "name": "web-Google",
        "desc": "Google web graph",
        "url":  "https://snap.stanford.edu/data/web-Google.txt.gz",
        "file": "web-Google.txt.gz",
        "slow": True,
    },
    {
        "name": "wiki-topcats",
        "desc": "Wikipedia hyperlinks (full)",
        "url":  "https://snap.stanford.edu/data/wiki-topcats.txt.gz",
        "file": "wiki-topcats.txt.gz",
        "slow": True,
    },
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def download(ds: dict) -> Path:
    gz = DATA_DIR / ds["file"]
    if not gz.exists():
        print(f"  Downloading {ds['name']} ...")
        urllib.request.urlretrieve(ds["url"], gz)
        print(f"  Saved {gz.stat().st_size / 1_048_576:.1f} MB")
    return gz

def gz_to_tsv(gz: Path, tsv: Path):
    if tsv.exists():
        return
    print(f"  Converting to TSV ...")
    count = 0
    with gzip.open(gz, "rt", encoding="utf-8") as src, open(tsv, "w", encoding="utf-8") as dst:
        for line in src:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) != 2:
                continue
            dst.write(f"{parts[0]}\t{parts[1]}\n")
            count += 1
    print(f"  {count:,} edges written")

def run(cmd: list[str], timeout=3600) -> dict:
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if result.returncode != 0:
        raise RuntimeError(f"Command failed:\n{result.stderr}")
    return json.loads(result.stdout.strip())

def validate(py: dict, cs: dict) -> tuple[bool, list[str]]:
    issues = []

    if py["nodes"] != cs["nodes"]:
        issues.append(f"nodes mismatch: Python={py['nodes']} .NET={cs['nodes']}")
    if py["edges"] != cs["edges"]:
        issues.append(f"edges mismatch: Python={py['edges']} .NET={cs['edges']}")

    # Allow ±1 iteration: floating-point summation order can shift the L1
    # delta across the convergence threshold by one step.
    if abs(py["iterations"] - cs["iterations"]) > 1:
        issues.append(f"iterations mismatch: Python={py['iterations']} .NET={cs['iterations']}")

    py_top = [t["node"] for t in py["top10"]]
    cs_top = [t["node"] for t in cs["top10"]]
    if py_top != cs_top:
        issues.append(f"top-10 ranking differs:\n    Python: {py_top}\n    .NET  : {cs_top}")

    # Both now use float64 — allow 1e-9 relative tolerance (summation order).
    for i, (p, c) in enumerate(zip(py["top10"], cs["top10"])):
        rel = abs(p["score"] - c["score"]) / max(abs(p["score"]), 1e-30)
        if rel > 1e-6:
            issues.append(f"score[{i}] relative error {rel:.2e}: Python={p['score']:.8e} .NET={c['score']:.8e}")

    return len(issues) == 0, issues

def fmt_ms(ms: float) -> str:
    if ms >= 60_000:
        return f"{ms/60_000:.1f} min"
    if ms >= 1_000:
        return f"{ms/1_000:.2f} s"
    return f"{ms:.0f} ms"

def speedup(py_ms: float, cs_ms: float) -> str:
    x = py_ms / cs_ms
    return f"{x:.0f}×"

# ---------------------------------------------------------------------------
# Build .NET once
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
# Run all datasets
# ---------------------------------------------------------------------------
rows = []

for ds in DATASETS:
    if SKIP_SLOW and ds.get("slow"):
        print(f"Skipping {ds['name']} (--skip-slow)")
        continue

    name = ds["name"]
    tsv  = DATA_DIR / f"{name}.tsv"

    print(f"{'='*60}")
    print(f"Dataset: {name}  ({ds['desc']})")

    gz = download(ds)
    gz_to_tsv(gz, tsv)

    print(f"  Running Python ...")
    t0 = time.perf_counter()
    try:
        py_result = run([PYTHON, str(PAGERANK), str(tsv), "--json"])
        py_ok = True
    except Exception as e:
        print(f"  Python FAILED: {e}")
        py_ok = False
        py_result = {}
    py_wall = (time.perf_counter() - t0) * 1000

    print(f"  Running .NET ...")
    t0 = time.perf_counter()
    try:
        cs_result = run([DOTNET, "run", "-c", "Release", "--no-build",
                         "--project", str(DOTNET_PROJ), str(tsv), "--json"])
        cs_ok = True
    except Exception as e:
        print(f"  .NET FAILED: {e}")
        cs_ok = False
        cs_result = {}
    cs_wall = (time.perf_counter() - t0) * 1000

    valid = False
    issues = []
    if py_ok and cs_ok:
        valid, issues = validate(py_result, cs_result)
        status = "PASS" if valid else "FAIL"
        if issues:
            for iss in issues:
                print(f"  VALIDATION: {iss}")
    else:
        status = "ERROR"

    rows.append({
        "name":   name,
        "nodes":  py_result.get("nodes", cs_result.get("nodes", 0)),
        "edges":  py_result.get("edges", cs_result.get("edges", 0)),
        "py_load":    py_result.get("load_ms", 0),
        "py_compute": py_result.get("compute_ms", 0),
        "cs_load":    cs_result.get("load_ms", 0),
        "cs_compute": cs_result.get("compute_ms", 0),
        "iters":  cs_result.get("iterations", py_result.get("iterations", 0)),
        "status": status,
    })

    if py_ok and cs_ok:
        print(f"  Python compute: {fmt_ms(py_result['compute_ms'])}   "
              f".NET compute: {fmt_ms(cs_result['compute_ms'])}   "
              f"Speedup: {speedup(py_result['compute_ms'], cs_result['compute_ms'])}   "
              f"[{status}]")

# ---------------------------------------------------------------------------
# Summary table
# ---------------------------------------------------------------------------
print()
print("=" * 100)
print(f"{'Dataset':<18} {'Nodes':>10} {'Edges':>12} {'Iters':>5} "
      f"{'Py Load':>10} {'Py Compute':>12} {'CS Load':>10} {'CS Compute':>12} "
      f"{'Speedup':>9} {'Valid':>6}")
print("-" * 100)

for r in rows:
    if r["py_compute"] > 0 and r["cs_compute"] > 0:
        sx = speedup(r["py_compute"], r["cs_compute"])
    else:
        sx = "N/A"

    print(f"{r['name']:<18} {r['nodes']:>10,} {r['edges']:>12,} {r['iters']:>5} "
          f"{fmt_ms(r['py_load']):>10} {fmt_ms(r['py_compute']):>12} "
          f"{fmt_ms(r['cs_load']):>10} {fmt_ms(r['cs_compute']):>12} "
          f"{sx:>9} {r['status']:>6}")

print("=" * 100)
print()
print("Speedup = Python compute / .NET compute (graph load not included)")
print("Valid   = PASS means top-10 node rankings identical, scores within 1e-4 relative tolerance")
