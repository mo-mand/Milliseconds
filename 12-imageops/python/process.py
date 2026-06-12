"""
scikit-image image-processing benchmark.

Pipeline per image:
  load JPEG -> resize 256x256 (anti_aliasing=True) -> Gaussian blur (sigma=2)
  -> grayscale -> encode JPEG (q=85)

Usage:
    python process.py <images_dir> [--json]
"""

import io, json, sys, time
import numpy as np
from pathlib import Path
from skimage import io as skio, transform, filters, color
from PIL import Image


def process_one(data: bytes) -> int:
    img = skio.imread(io.BytesIO(data))                           # H x W x 3, uint8
    img = transform.resize(img, (256, 256), anti_aliasing=True)  # float64 [0,1]
    img = filters.gaussian(img, sigma=2, channel_axis=-1)        # blur per channel
    img = color.rgb2gray(img)                                     # float64 [0,1]
    # encode to JPEG via Pillow (matches .NET side)
    pil = Image.fromarray((img * 255).astype(np.uint8), mode="L")
    buf = io.BytesIO()
    pil.save(buf, format="JPEG", quality=85)
    return int((img * 255).sum())


def main():
    json_mode = "--json" in sys.argv
    path_args = [a for a in sys.argv[1:] if not a.startswith("--")]

    data_dir = Path(path_args[0]) if path_args else (
        Path(__file__).parent.parent / "data" / "images_1k"
    )

    files = sorted(data_dir.glob("*.jpg"))
    if not files:
        print(f"No .jpg files in {data_dir}", file=sys.stderr)
        sys.exit(1)

    raw = [f.read_bytes() for f in files]

    start = time.perf_counter()
    checksum = sum(process_one(b) for b in raw)
    elapsed_ms = (time.perf_counter() - start) * 1000

    if json_mode:
        print(json.dumps({
            "images":     len(raw),
            "elapsed_ms": elapsed_ms,
            "checksum":   checksum,
        }))
    else:
        print(f"Images  : {len(raw):,}")
        print(f"Elapsed : {elapsed_ms:,.0f} ms  ({elapsed_ms / len(raw):.1f} ms/image)")
        print(f"Checksum: {checksum:,}")


if __name__ == "__main__":
    main()
