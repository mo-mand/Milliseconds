from PIL import Image
from pathlib import Path

QUALITY = 88  # 85-92 is the sweet spot — good visuals, small file

def convert(png_path: Path):
    jpg_path = png_path.with_suffix(".jpg")
    img = Image.open(png_path).convert("RGB")
    img.save(jpg_path, "JPEG", quality=QUALITY, optimize=True)
    before = png_path.stat().st_size / 1024
    after  = jpg_path.stat().st_size / 1024
    print(f"{png_path.name}  ->  {jpg_path.name}  ({before:.0f} KB -> {after:.0f} KB)")

# Convert every Diagram*.png in every project subfolder
root = Path(__file__).parent
for png in sorted(root.glob("*/Diagram*.png")):
    convert(png)
