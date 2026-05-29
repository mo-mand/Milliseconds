"""
Generate QR code input datasets — realistic mix of URLs, plain text, and
alphanumeric codes covering QR versions 1-10.

Outputs (in data/):
    inputs_10k.txt    10 000 strings
    inputs_50k.txt    50 000 strings
    inputs_100k.txt  100 000 strings

Usage:
    python build_inputs.py
"""

import random
import string
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

rng = random.Random(42)

DOMAINS = ["example.com", "openai.com", "github.com", "wikipedia.org",
           "stackoverflow.com", "arxiv.org", "python.org", "dotnet.microsoft.com"]
WORDS   = ["performance", "benchmark", "dotnet", "python", "speed",
           "memory", "throughput", "latency", "encoding", "matrix",
           "render", "parse", "index", "search", "compute"]

def rand_url():
    domain = rng.choice(DOMAINS)
    path   = "/".join(rng.choice(WORDS) for _ in range(rng.randint(1, 4)))
    param  = f"?id={rng.randint(1000, 99999)}" if rng.random() < 0.5 else ""
    return f"https://{domain}/{path}{param}"

def rand_text():
    n = rng.randint(2, 8)
    return " ".join(rng.choice(WORDS) for _ in range(n))

def rand_alphanum():
    n = rng.randint(8, 32)
    return "".join(rng.choices(string.ascii_uppercase + string.digits, k=n))

GENERATORS = [rand_url, rand_text, rand_alphanum]

TARGETS = {
    "inputs_10k.txt":  10_000,
    "inputs_50k.txt":  50_000,
    "inputs_100k.txt": 100_000,
}

for name, n in TARGETS.items():
    out = DATA_DIR / name
    if out.exists():
        print(f"  {name} already exists -- skipping")
        continue
    lines = [rng.choice(GENERATORS)() for _ in range(n)]
    out.write_bytes(("\n".join(lines) + "\n").encode("utf-8"))
    print(f"  {name}: {n:,} inputs  ({out.stat().st_size // 1024:,} KB)")

print("\nDone.")
