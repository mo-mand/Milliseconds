# 02 — PageRank on Wikipedia Link Graph

**Algorithm:** Power-iteration PageRank (damping=0.85, tol=1e-6)  
**Dataset:** Stanford SNAP `wiki-topcats` — 1.8 M nodes, 28.5 M edges (pure public domain data, no C++ dependency)

| Runtime | Implementation |
|---------|---------------|
| Python  | NetworkX 3.x — 100% pure Python, zero C extensions |
| .NET 10 | CSR sparse matrix + TensorPrimitives SIMD (AVX-512 / AVX2) |

## Quick start

```
# 1. Download real data (~75 MB compressed)
python python/download_data.py

# 2. Run Python baseline
pip install -r python/requirements.txt
python python/pagerank.py

# 3. Run .NET
dotnet run -c Release --project dotnet/PageRank.csproj
```

Use `--small` for a smoke-test on the 7 k-node wiki-vote graph:
```
python python/download_data.py --small
```

## Why this is a fair comparison

NetworkX is **pure Python** — all graph traversal and arithmetic runs in the CPython interpreter with no native extension involved. The .NET version uses the same algorithm (power iteration with dangling-node correction) on the same CSR representation, but the inner loop benefits from JIT compilation and SIMD vectorisation through `TensorPrimitives`.
