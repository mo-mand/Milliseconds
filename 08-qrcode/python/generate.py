"""
QR code generation benchmark - pure Python, qrcode library.

Uses qrcode>=7.4 with the pure-Python implementation (no C extensions required).
Counts dark modules across all generated codes as the validation checksum.

Usage:
    python generate.py [path/to/inputs.txt] [--json]
"""

import sys
import json
import time
from pathlib import Path

try:
    import qrcode
    from qrcode.constants import ERROR_CORRECT_M
except ImportError:
    sys.exit("qrcode not installed. Run: pip install qrcode")

JSON_MODE = "--json" in sys.argv
path_args = [a for a in sys.argv[1:] if not a.startswith("--")]

inputs_path = Path(path_args[0]) if path_args else \
              Path(__file__).parent.parent / "data" / "inputs_10k.txt"

if not inputs_path.exists():
    sys.exit(f"File not found: {inputs_path}\nRun: python build_inputs.py")

def log(msg):
    if not JSON_MODE:
        print(msg, flush=True)

log(f"Loading inputs from: {inputs_path}")
lines = [l for l in inputs_path.read_text(encoding="utf-8").splitlines() if l.strip()]
log(f"Inputs: {len(lines):,}")

t0 = time.perf_counter()
total_dark = 0
total_size = 0

for text in lines:
    qr = qrcode.QRCode(error_correction=ERROR_CORRECT_M, box_size=1, border=0)
    qr.add_data(text)
    qr.make(fit=True)
    matrix = qr.get_matrix()
    total_size += len(matrix)
    for row in matrix:
        total_dark += sum(1 for cell in row if cell)

elapsed_ms = (time.perf_counter() - t0) * 1000

if JSON_MODE:
    print(json.dumps({
        "codes":      len(lines),
        "dark_mods":  total_dark,
        "total_size": total_size,
        "elapsed_ms": round(elapsed_ms, 1),
    }))
else:
    print(f"\nCodes       : {len(lines):,}")
    print(f"Dark modules: {total_dark:,}")
    print(f"Elapsed     : {elapsed_ms:.1f} ms")
    print(f"Throughput  : {len(lines) / (elapsed_ms / 1000):.0f} codes/s")
