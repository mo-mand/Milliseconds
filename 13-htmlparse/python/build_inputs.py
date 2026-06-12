"""
Generate synthetic HTML documents for the benchmark.
Each document simulates a product listing page with nav links, a table, and article links.

Usage:
    python build_inputs.py
"""

import random
from pathlib import Path

DATA = Path(__file__).parent.parent / "data"
SIZES = [("docs_5k", 5_000), ("docs_20k", 20_000), ("docs_50k", 50_000)]

CATEGORIES = ["Electronics", "Clothing", "Books", "Sports", "Home", "Garden", "Toys", "Food"]
REGIONS    = ["North", "South", "East", "West", "Central"]

def make_html(seed: int) -> str:
    rng = random.Random(seed)
    cat = rng.choice(CATEGORIES)
    region = rng.choice(REGIONS)
    n_rows = rng.randint(5, 15)
    n_links = rng.randint(3, 8)

    rows = "\n".join(
        f'<tr><td>Item {i}</td><td>{rng.randint(1,500)}</td>'
        f'<td>${rng.uniform(1,999):.2f}</td><td>{rng.choice(REGIONS)}</td></tr>'
        for i in range(1, n_rows + 1)
    )
    links = "\n".join(
        f'<li><a href="/products/{rng.randint(1000,9999)}">Product {i}</a></li>'
        for i in range(1, n_links + 1)
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>{cat} — {region} Report</title></head>
<body>
<nav>
  <a href="/">Home</a>
  <a href="/products">Products</a>
  <a href="/reports">Reports</a>
  <a href="/contact">Contact</a>
</nav>
<h1>{cat} Sales Report — {region}</h1>
<p>Generated for region <strong>{region}</strong> with {n_rows} entries.</p>
<table>
  <thead><tr><th>Name</th><th>Qty</th><th>Price</th><th>Region</th></tr></thead>
  <tbody>{rows}</tbody>
</table>
<h2>Related Products</h2>
<ul>{links}</ul>
<footer><p>Page {seed} of 10000</p></footer>
</body>
</html>"""


for folder_name, count in SIZES:
    folder = DATA / folder_name
    folder.mkdir(parents=True, exist_ok=True)
    existing = len(list(folder.glob("*.html")))
    if existing >= count:
        print(f"  {folder_name}: already has {existing} files, skipping.")
        continue
    print(f"Generating {count:,} HTML files -> {folder_name}/ ...")
    for i in range(count):
        (folder / f"{i:05d}.html").write_text(make_html(i), encoding="utf-8")
        if i and i % 10000 == 0:
            print(f"  {i:,} / {count:,}")
    print(f"  Done.")

print("\nAll datasets ready.")
