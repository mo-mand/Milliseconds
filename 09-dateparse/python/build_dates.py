"""
Generate date string datasets covering 8 common formats.

Outputs (in data/):
    dates_100k.txt    100 000 date strings
    dates_500k.txt    500 000 date strings
    dates_1m.txt    1 000 000 date strings

Each line is one date string in one of the supported formats.

Usage:
    python build_dates.py
"""

import random
from datetime import datetime, timedelta
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

rng = random.Random(42)

# Date range: 1970-01-01 to 2030-12-31
START = datetime(1970, 1, 1)
DAYS  = (datetime(2030, 12, 31) - START).days

MONTHS_SHORT = ["Jan","Feb","Mar","Apr","May","Jun",
                "Jul","Aug","Sep","Oct","Nov","Dec"]
MONTHS_LONG  = ["January","February","March","April","May","June",
                "July","August","September","October","November","December"]
DAYS_SHORT   = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]

def rand_dt():
    d = START + timedelta(days=rng.randint(0, DAYS))
    h, m, s = rng.randint(0, 23), rng.randint(0, 59), rng.randint(0, 59)
    return d.replace(hour=h, minute=m, second=s)

def fmt_iso(dt):          return dt.strftime("%Y-%m-%dT%H:%M:%S")
def fmt_date(dt):         return dt.strftime("%Y-%m-%d")
def fmt_rfc2822(dt):
    wd = DAYS_SHORT[dt.weekday()]
    mo = MONTHS_SHORT[dt.month - 1]
    return f"{wd}, {dt.day:02d} {mo} {dt.year} {dt.hour:02d}:{dt.minute:02d}:{dt.second:02d} +0000"
def fmt_long(dt):         return f"{MONTHS_LONG[dt.month-1]} {dt.day}, {dt.year}"
def fmt_us(dt):           return f"{dt.month}/{dt.day}/{dt.year}"
def fmt_day_mon(dt):
    mo = MONTHS_SHORT[dt.month - 1]
    return f"{dt.day:02d} {mo} {dt.year}"
def fmt_slash(dt):        return dt.strftime("%Y/%m/%d %H:%M:%S")
def fmt_us_hm(dt):        return dt.strftime("%m-%d-%Y %H:%M")

FORMATTERS = [fmt_iso, fmt_date, fmt_rfc2822, fmt_long,
              fmt_us, fmt_day_mon, fmt_slash, fmt_us_hm]

TARGETS = {
    "dates_100k.txt":   100_000,
    "dates_500k.txt":   500_000,
    "dates_1m.txt":   1_000_000,
}

for name, n in TARGETS.items():
    out = DATA_DIR / name
    if out.exists():
        print(f"  {name} already exists -- skipping")
        continue
    lines = [rng.choice(FORMATTERS)(rand_dt()) for _ in range(n)]
    out.write_bytes(("\n".join(lines) + "\n").encode("utf-8"))
    print(f"  {name}: {n:,} dates  ({out.stat().st_size // 1024:,} KB)")

print("\nDone.")
