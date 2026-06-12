"""
Generate synthetic JPEG test images (400×300, color gradients + shapes).
Run once before benchmarking.

Usage:
    python build_inputs.py
"""

import random
from pathlib import Path
from PIL import Image, ImageDraw

DATA = Path(__file__).parent.parent / "data"

SIZES = [
    ("images_1k",  1_000),
    ("images_5k",  5_000),
    ("images_10k", 10_000),
]

def make_image(seed: int) -> Image.Image:
    rng = random.Random(seed)
    bg = (rng.randint(30, 220), rng.randint(30, 220), rng.randint(30, 220))
    img = Image.new("RGB", (400, 300), bg)
    draw = ImageDraw.Draw(img)
    for _ in range(12):
        x1 = rng.randint(0, 350)
        y1 = rng.randint(0, 250)
        x2 = x1 + rng.randint(30, 120)
        y2 = y1 + rng.randint(30, 100)
        color = (rng.randint(0, 255), rng.randint(0, 255), rng.randint(0, 255))
        if rng.random() > 0.5:
            draw.ellipse([x1, y1, x2, y2], fill=color)
        else:
            draw.rectangle([x1, y1, x2, y2], fill=color)
    return img

for folder_name, count in SIZES:
    folder = DATA / folder_name
    folder.mkdir(parents=True, exist_ok=True)
    existing = len(list(folder.glob("*.jpg")))
    if existing >= count:
        print(f"  {folder_name}: already has {existing} images, skipping.")
        continue
    print(f"Generating {count:,} images -> {folder_name}/ ...")
    for i in range(count):
        make_image(i).save(folder / f"{i:05d}.jpg", format="JPEG", quality=90)
        if i and i % 1000 == 0:
            print(f"  {i:,} / {count:,}")
    print(f"  Done.")

print("\nAll datasets ready.")
