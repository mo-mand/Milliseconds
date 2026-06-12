"""
Image processing benchmark: Python (Pillow) vs .NET 10 (ImageSharp).

Pipeline per image: load JPEG → resize 256×256 → Gaussian blur → grayscale → encode JPEG.
Validates that pixel checksums are within 3% between runtimes.

Usage:
    python benchmark_all.py
"""

import sys, json, subprocess
from pathlib import Path

ROOT        = Path(__file__).parent.parent
DATA_DIR    = ROOT / "data"
DOTNET      = r"C:\Program Files\dotnet\dotnet.exe"
DOTNET_PROJ = ROOT / "dotnet" / "ImageOps.csproj"
PYTHON      = sys.executable
BENCH       = Path(__file__).parent / "process.py"

DATASETS = [
    ("1k",  DATA_DIR / "images_1k"),
    ("5k",  DATA_DIR / "images_5k"),
    ("10k", DATA_DIR / "images_10k"),
]


def run(cmd, timeout=3600):
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError(r.stderr[:500])
    return json.loads(r.stdout.strip())


def fmt(ms):
    if ms >= 60_000: return f"{ms / 60_000:.2f} min"
    if ms >= 1_000:  return f"{ms / 1_000:.2f} s"
    return f"{ms:.0f} ms"


def speedup(py, cs):
    return f"{py / cs:.1f}x"


def validate(py, cs):
    issues = []
    if py["images"] != cs["images"]:
        issues.append(f"image count mismatch: Python={py['images']:,} .NET={cs['images']:,}")
    # Blur kernel and JPEG codec differ slightly — allow 3% tolerance on checksum
    if py["checksum"] > 0:
        ratio = abs(py["checksum"] - cs["checksum"]) / py["checksum"]
        if ratio > 0.03:
            issues.append(
                f"checksum differs {ratio*100:.1f}%: "
                f"Python={py['checksum']:,} .NET={cs['checksum']:,}"
            )
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
    if not path.exists() or not any(path.glob("*.jpg")):
        print(f"Skipping {label} — run build_inputs.py first.")
        continue

    count = len(list(path.glob("*.jpg")))
    print(f"{'=' * 55}")
    print(f"Dataset: {label}  ({count:,} images, {sum(f.stat().st_size for f in path.glob('*.jpg')) // 1024 // 1024} MB)")

    print("  Running Python (Pillow) ...")
    try:
        py = run([PYTHON, str(BENCH), str(path), "--json"])
        py_ok = True
    except Exception as e:
        print(f"  Python FAILED: {e}"); py_ok = False; py = {}

    print("  Running .NET (ImageSharp) ...")
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
        "images": py.get("images", cs.get("images", 0)),
        "py_ms":  py.get("elapsed_ms", 0),
        "cs_ms":  cs.get("elapsed_ms", 0),
        "status": status,
    })

# ---- Summary ----------------------------------------------------------------
print()
print("=" * 65)
print(f"{'Images':<8} {'Python':>12} {'.NET':>10} {'Speedup':>10} {'Valid':>6}")
print("-" * 65)
for r in rows:
    sx = speedup(r["py_ms"], r["cs_ms"]) if r["py_ms"] and r["cs_ms"] else "N/A"
    print(f"{r['label']:<8} {fmt(r['py_ms']):>12} {fmt(r['cs_ms']):>10} {sx:>10} {r['status']:>6}")
print("=" * 65)
