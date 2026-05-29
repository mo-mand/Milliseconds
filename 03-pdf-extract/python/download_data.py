"""
Download real arXiv PDF papers for the benchmark.

Fetches papers from the arXiv API (cs.LG category) and downloads their PDFs.
Papers are public domain / open access — no license issues.

Usage:
    python download_data.py [--count N]   (default: 200)

Output: data/pdfs/*.pdf
"""

import sys
import time
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from pathlib import Path

COUNT = 200
for arg in sys.argv[1:]:
    if arg.startswith("--count"):
        COUNT = int(arg.split("=")[-1]) if "=" in arg else int(sys.argv[sys.argv.index(arg) + 1])

PDF_DIR = Path(__file__).parent.parent / "data" / "pdfs"
PDF_DIR.mkdir(parents=True, exist_ok=True)

ARXIV_API = (
    "http://export.arxiv.org/api/query"
    "?search_query=cat:cs.LG"
    "&sortBy=submittedDate&sortOrder=descending"
    f"&max_results={COUNT}"
)
NS = "http://www.w3.org/2005/Atom"

# ---- Fetch paper IDs from API -----------------------------------------------
print(f"Fetching {COUNT} paper IDs from arXiv API ...")
with urllib.request.urlopen(ARXIV_API, timeout=30) as r:
    xml_data = r.read()

root = ET.fromstring(xml_data)
entries = root.findall(f"{{{NS}}}entry")
ids = []
for entry in entries:
    id_url = entry.find(f"{{{NS}}}id").text.strip()   # e.g. http://arxiv.org/abs/2401.12345v1
    arxiv_id = id_url.split("/abs/")[-1]              # 2401.12345v1
    ids.append(arxiv_id)

print(f"Got {len(ids)} paper IDs")

# ---- Download PDFs ----------------------------------------------------------
downloaded = 0
skipped    = 0
failed     = 0

for i, arxiv_id in enumerate(ids):
    safe_id = arxiv_id.replace("/", "_")
    dest = PDF_DIR / f"{safe_id}.pdf"

    if dest.exists() and dest.stat().st_size > 1024:
        skipped += 1
        continue

    url = f"https://arxiv.org/pdf/{arxiv_id}"
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            data = r.read()
        if len(data) < 1024:
            failed += 1
            continue
        dest.write_bytes(data)
        downloaded += 1
        print(f"  [{i+1}/{len(ids)}] {arxiv_id}  ({len(data)//1024} KB)")
        time.sleep(0.5)          # be polite to arXiv
    except (urllib.error.URLError, TimeoutError) as e:
        print(f"  [{i+1}/{len(ids)}] FAILED {arxiv_id}: {e}")
        failed += 1
        time.sleep(1)

total = len(list(PDF_DIR.glob("*.pdf")))
print(f"\nDone. downloaded={downloaded}  skipped={skipped}  failed={failed}")
print(f"Total PDFs in data/pdfs/: {total}")
print()
print("Next steps:")
print("  python python/extract.py          # Python baseline")
print("  dotnet run -c Release --project dotnet/PdfExtract.csproj   # .NET")
