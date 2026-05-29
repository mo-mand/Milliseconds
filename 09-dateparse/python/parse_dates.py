"""
Date string parsing benchmark - pure Python, python-dateutil.

Uses dateutil.parser.parse() — the classic pure-Python flexible date parser.

Usage:
    python parse_dates.py [path/to/dates.txt] [--json]
"""

import sys
import json
import time
from pathlib import Path

try:
    from dateutil import parser as duparser
except ImportError:
    sys.exit("python-dateutil not installed. Run: pip install python-dateutil")

JSON_MODE = "--json" in sys.argv
path_args = [a for a in sys.argv[1:] if not a.startswith("--")]

dates_path = Path(path_args[0]) if path_args else \
             Path(__file__).parent.parent / "data" / "dates_100k.txt"

if not dates_path.exists():
    sys.exit(f"File not found: {dates_path}\nRun: python build_dates.py")

def log(msg):
    if not JSON_MODE:
        print(msg, flush=True)

log(f"Loading dates from: {dates_path}")
lines = [l for l in dates_path.read_text(encoding="utf-8").splitlines() if l.strip()]
log(f"Dates: {len(lines):,}")

t0 = time.perf_counter()
checksum = 0
failed = 0

for line in lines:
    try:
        dt = duparser.parse(line)
        checksum += dt.year * 10000 + dt.month * 100 + dt.day
    except Exception:
        failed += 1

elapsed_ms = (time.perf_counter() - t0) * 1000

if JSON_MODE:
    print(json.dumps({
        "dates":      len(lines),
        "checksum":   checksum,
        "failed":     failed,
        "elapsed_ms": round(elapsed_ms, 1),
    }))
else:
    print(f"\nChecksum  : {checksum:,}")
    print(f"Failed    : {failed:,}")
    print(f"Elapsed   : {elapsed_ms:.1f} ms")
    print(f"Throughput: {len(lines) / (elapsed_ms / 1000):.0f} dates/s")
