from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageFilter


def main() -> None:
    parser = argparse.ArgumentParser(description="为 HyperFrames 产品动效生成透明素材")
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    _save_transparent(input_dir / "AI眼镜.png", output_dir / "AI眼镜.png")
    _save_transparent(input_dir / "AI眼镜盒.png", output_dir / "AI眼镜盒.png")


def _save_transparent(input_path: Path, output_path: Path) -> None:
    image = Image.open(input_path).convert("RGBA")
    alpha = Image.new("L", image.size, 0)
    source_pixels = image.load()
    alpha_pixels = alpha.load()

    for y in range(image.height):
        for x in range(image.width):
            red, green, blue, _old_alpha = source_pixels[x, y]
            whiteness = (red + green + blue) / 3
            color_distance = abs(red - 255) + abs(green - 255) + abs(blue - 255)
            if whiteness > 238 and color_distance < 58:
                alpha_pixels[x, y] = 0
            else:
                alpha_pixels[x, y] = min(255, int(max(0, color_distance - 24) * 4.8))

    image.putalpha(alpha.filter(ImageFilter.GaussianBlur(radius=0.35)))
    bbox = image.getbbox()
    if bbox is None:
        raise ValueError(f"素材没有有效内容：{input_path}")
    image.crop(bbox).save(output_path)


if __name__ == "__main__":
    main()
