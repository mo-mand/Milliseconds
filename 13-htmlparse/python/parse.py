"""
BeautifulSoup4 HTML parsing benchmark.

Per document:
  parse HTML -> find all <a> hrefs -> count <td> cells -> extract <h1> text

Usage:
    python parse.py <docs_dir> [--json]
"""

import json, sys, time
from pathlib import Path
from bs4 import BeautifulSoup


def parse_one(html: str) -> tuple[int, int, str]:
    soup  = BeautifulSoup(html, "html.parser")
    hrefs = [a["href"] for a in soup.find_all("a", href=True)]
    tds   = len(soup.find_all("td"))
    h1    = (soup.find("h1") or {}).get_text(strip=True) if soup.find("h1") else ""
    return len(hrefs), tds, h1


def main():
    json_mode = "--json" in sys.argv
    path_args = [a for a in sys.argv[1:] if not a.startswith("--")]
    data_dir  = Path(path_args[0]) if path_args else (
        Path(__file__).parent.parent / "data" / "docs_5k"
    )

    files = sorted(data_dir.glob("*.html"))
    if not files:
        print(f"No .html files in {data_dir}", file=sys.stderr)
        sys.exit(1)

    raw = [f.read_text(encoding="utf-8") for f in files]

    start      = time.perf_counter()
    total_hrefs = total_tds = 0
    for doc in raw:
        h, t, _ = parse_one(doc)
        total_hrefs += h
        total_tds   += t
    elapsed_ms = (time.perf_counter() - start) * 1000

    if json_mode:
        print(json.dumps({
            "docs":       len(raw),
            "elapsed_ms": elapsed_ms,
            "total_hrefs": total_hrefs,
            "total_tds":  total_tds,
        }))
    else:
        print(f"Docs   : {len(raw):,}")
        print(f"Elapsed: {elapsed_ms:,.0f} ms  ({elapsed_ms / len(raw):.2f} ms/doc)")
        print(f"Hrefs  : {total_hrefs:,}   TDs: {total_tds:,}")


if __name__ == "__main__":
    main()
