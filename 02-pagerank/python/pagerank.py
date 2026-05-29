"""
PageRank — pure Python, zero C extensions.

Uses list-based CSR (same structure as .NET) for fairest comparison.
No numpy, no scipy, no networkx, no ctypes.

Usage:
    python pagerank.py [path/to/links.tsv] [--json]
"""

import sys
import time
import json
from pathlib import Path
from array import array

JSON_MODE = "--json" in sys.argv
args = [a for a in sys.argv[1:] if not a.startswith("--")]
DATA = Path(args[0]) if args else Path(__file__).parent.parent / "data" / "links.tsv"

if not DATA.exists():
    sys.exit(f"Data file not found: {DATA}\nRun: python download_data.py")

def log(msg):
    if not JSON_MODE:
        print(msg, flush=True)

# ---- Load & build CSR -------------------------------------------------------
log(f"Loading graph from: {DATA}")
t0 = time.perf_counter()

raw_edges: list[tuple[int, int]] = []
max_id = 0

with open(DATA, encoding="utf-8") as f:
    for line in f:
        if not line or line[0] == "#":
            continue
        tab = line.find("\t")
        if tab < 0:
            continue
        u = int(line[:tab])
        v = int(line[tab+1:])
        if u > max_id: max_id = u
        if v > max_id: max_id = v
        raw_edges.append((u, v))

n = max_id + 1
E = len(raw_edges)

out_deg = array("i", [0] * n)
for u, _ in raw_edges:
    out_deg[u] += 1

row_ptr = array("i", [0] * (n + 1))
for i in range(n):
    row_ptr[i + 1] = row_ptr[i] + out_deg[i]

col_idx = array("i", [0] * E)
pos = array("i", row_ptr)
for u, v in raw_edges:
    col_idx[pos[u]] = v
    pos[u] += 1

load_ms = (time.perf_counter() - t0) * 1000
log(f"Nodes: {n:,}   Edges: {E:,}   (loaded in {load_ms:.0f} ms)")

# ---- Power iteration --------------------------------------------------------
DAMPING  = 0.85
TOL      = 1e-6
MAX_ITER = 100

log("Running PageRank (damping=0.85, tol=1e-6) ...")
t1 = time.perf_counter()

inv_n = 1.0 / n
rank     = [inv_n] * n
new_rank = [0.0]   * n

dangling_nodes = [u for u in range(n) if out_deg[u] == 0]

delta = float("inf")
iteration = 0

while iteration < MAX_ITER and delta > TOL:
    dangling = sum(rank[u] for u in dangling_nodes)
    base = (1.0 - DAMPING + DAMPING * dangling) / n

    for i in range(n):
        new_rank[i] = base

    for u in range(n):
        start = row_ptr[u]
        end   = row_ptr[u + 1]
        if start == end:
            continue
        contrib = DAMPING * rank[u] / (end - start)
        for k in range(start, end):
            new_rank[col_idx[k]] += contrib

    total = sum(new_rank)
    inv_total = 1.0 / total
    delta = 0.0
    for i in range(n):
        new_rank[i] *= inv_total
        delta += abs(new_rank[i] - rank[i])

    rank, new_rank = new_rank, rank
    iteration += 1

elapsed_ms = (time.perf_counter() - t1) * 1000

top10 = sorted(range(n), key=lambda i: rank[i], reverse=True)[:10]

if JSON_MODE:
    print(json.dumps({
        "nodes": n, "edges": E,
        "load_ms": round(load_ms, 1),
        "compute_ms": round(elapsed_ms, 1),
        "iterations": iteration,
        "delta": delta,
        "top10": [{"node": node, "score": rank[node]} for node in top10],
    }))
else:
    print(f"Converged: {iteration} iterations  delta={delta:.2E}")
    print(f"Elapsed  : {elapsed_ms:.1f} ms\n")
    print(f"{'Rank':<5} {'Node':>10} {'Score':>12}")
    print("-" * 30)
    for k, node in enumerate(top10, 1):
        print(f"{k:<5} {node:>10} {rank[node]:>12.4E}")
