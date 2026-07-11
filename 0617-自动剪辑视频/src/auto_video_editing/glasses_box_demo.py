from __future__ import annotations

import argparse
import math
import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter


CANVAS_SIZE = (1080, 1920)
FPS = 30
DURATION_SECONDS = 5


def main() -> None:
    parser = argparse.ArgumentParser(description="生成理想 AI 眼镜入盒 5 秒演示视频")
    parser.add_argument("--input-dir", default="inputs/理想AI眼镜")
    parser.add_argument("--output", default="outputs/理想AI眼镜-入盒演示-5s.mp4")
    args = parser.parse_args()

    root = Path.cwd()
    input_dir = root / args.input_dir
    output_path = root / args.output
    frame_dir = root / "outputs" / "work" / "ideal_glasses_frames"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    frame_dir.mkdir(parents=True, exist_ok=True)

    _require_ffmpeg()
    _clear_frames(frame_dir)
    _render_frames(input_dir, frame_dir)
    _encode_video(frame_dir, output_path)
    print(f"演示视频已生成：{output_path}")


def _render_frames(input_dir: Path, frame_dir: Path) -> None:
    glasses = _load_product_layer(input_dir / "AI眼镜.png")
    box = _load_product_layer(input_dir / "AI眼镜盒.png")
    box_layer = _resize_to_width(box, 980)
    total_frames = FPS * DURATION_SECONDS

    for index in range(total_frames):
        progress = index / (total_frames - 1)
        frame = _background(progress)
        box_pos = ((CANVAS_SIZE[0] - box_layer.width) // 2, 1120)
        frame.alpha_composite(box_layer, box_pos)
        _draw_contact_shadow(frame, box_pos, box_layer.size, progress)

        moving = _moving_glasses(glasses, progress)
        frame.alpha_composite(moving.image, moving.position)
        frame.alpha_composite(box_layer, box_pos)
        _draw_finish_glow(frame, box_pos, box_layer.size, progress)

        rgb = frame.convert("RGB")
        rgb.save(frame_dir / f"frame_{index:04d}.png", compress_level=1)


def _background(progress: float) -> Image.Image:
    width, height = CANVAS_SIZE
    image = Image.new("RGBA", CANVAS_SIZE, (246, 247, 244, 255))
    draw = ImageDraw.Draw(image, "RGBA")
    for y in range(height):
        tone = int(248 - 16 * (y / height))
        draw.line([(0, y), (width, y)], fill=(tone, tone, tone - 2, 255))
    glow_alpha = int(30 + 18 * math.sin(progress * math.pi))
    draw.ellipse((110, 680, 970, 1540), fill=(214, 224, 216, glow_alpha))
    return image.filter(ImageFilter.GaussianBlur(radius=0.2))


def _moving_glasses(source: Image.Image, progress: float) -> "PlacedLayer":
    enter = _smoothstep(_clamp(progress / 0.18))
    drop = _ease_in_out_cubic(_clamp((progress - 0.12) / 0.66))
    settle = _ease_out_back(_clamp((progress - 0.78) / 0.18))

    width = int(_lerp(920, 710, drop))
    image = _resize_to_width(source, width)
    opacity = _lerp(0.0, 1.0, enter) * _lerp(1.0, 0.72, _clamp((progress - 0.70) / 0.20))
    image = _apply_opacity(image, opacity)

    x = int((CANVAS_SIZE[0] - image.width) / 2 + _lerp(-46, 0, drop))
    y = int(_lerp(270, 1194, drop) - 28 * settle)
    return PlacedLayer(image=image, position=(x, y))


def _draw_contact_shadow(
    frame: Image.Image,
    box_pos: tuple[int, int],
    box_size: tuple[int, int],
    progress: float,
) -> None:
    shadow_progress = _clamp((progress - 0.34) / 0.46)
    if shadow_progress <= 0:
        return
    alpha = int(68 * math.sin(shadow_progress * math.pi))
    layer = Image.new("RGBA", CANVAS_SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer, "RGBA")
    cx = box_pos[0] + box_size[0] // 2
    cy = box_pos[1] + 130
    w = int(_lerp(580, 390, shadow_progress))
    h = int(_lerp(68, 36, shadow_progress))
    draw.ellipse((cx - w // 2, cy - h // 2, cx + w // 2, cy + h // 2), fill=(33, 28, 22, alpha))
    frame.alpha_composite(layer.filter(ImageFilter.GaussianBlur(radius=16)))


def _draw_finish_glow(
    frame: Image.Image,
    box_pos: tuple[int, int],
    box_size: tuple[int, int],
    progress: float,
) -> None:
    glow = math.sin(_clamp((progress - 0.80) / 0.20) * math.pi)
    if glow <= 0:
        return
    layer = Image.new("RGBA", CANVAS_SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer, "RGBA")
    cx = box_pos[0] + box_size[0] // 2
    cy = box_pos[1] + int(box_size[1] * 0.73)
    draw.rounded_rectangle(
        (cx - 74, cy - 9, cx + 74, cy + 9),
        radius=9,
        fill=(124, 240, 160, int(95 * glow)),
    )
    frame.alpha_composite(layer.filter(ImageFilter.GaussianBlur(radius=6)))


def _load_product_layer(path: Path) -> Image.Image:
    if not path.exists():
        raise FileNotFoundError(f"找不到素材：{path}")
    image = Image.open(path).convert("RGBA")
    alpha = Image.new("L", image.size, 0)
    pixels = image.load()
    alpha_pixels = alpha.load()
    for y in range(image.height):
        for x in range(image.width):
            red, green, blue, _old_alpha = pixels[x, y]
            distance = min(255, abs(red - 255) + abs(green - 255) + abs(blue - 255))
            value = 0 if distance < 28 else min(255, int((distance - 18) * 5.5))
            alpha_pixels[x, y] = value
    image.putalpha(alpha.filter(ImageFilter.GaussianBlur(radius=0.25)))
    bbox = image.getbbox()
    if bbox is None:
        raise ValueError(f"素材没有有效图层：{path}")
    return image.crop(bbox)


def _resize_to_width(image: Image.Image, width: int) -> Image.Image:
    height = int(image.height * width / image.width)
    return image.resize((width, height), Image.Resampling.LANCZOS)


def _apply_opacity(image: Image.Image, opacity: float) -> Image.Image:
    result = image.copy()
    alpha = result.getchannel("A").point(lambda value: int(value * opacity))
    result.putalpha(alpha)
    return result


def _encode_video(frame_dir: Path, output_path: Path) -> None:
    command = [
        "ffmpeg",
        "-y",
        "-framerate",
        str(FPS),
        "-i",
        str(frame_dir / "frame_%04d.png"),
        "-vf",
        "format=yuv420p",
        "-c:v",
        "libx264",
        "-movflags",
        "+faststart",
        "-r",
        str(FPS),
        str(output_path),
    ]
    subprocess.run(command, check=True)


def _clear_frames(frame_dir: Path) -> None:
    for frame in frame_dir.glob("frame_*.png"):
        frame.unlink()


def _require_ffmpeg() -> None:
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("未找到 ffmpeg，请先安装 ffmpeg")


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def _lerp(start: float, end: float, progress: float) -> float:
    return start + (end - start) * progress


def _smoothstep(value: float) -> float:
    x = _clamp(value)
    return x * x * (3 - 2 * x)


def _ease_in_out_cubic(value: float) -> float:
    x = _clamp(value)
    if x < 0.5:
        return 4 * x * x * x
    return 1 - pow(-2 * x + 2, 3) / 2


def _ease_out_back(value: float) -> float:
    x = _clamp(value)
    c1 = 1.70158
    c3 = c1 + 1
    return 1 + c3 * pow(x - 1, 3) + c1 * pow(x - 1, 2)


class PlacedLayer:
    def __init__(self, image: Image.Image, position: tuple[int, int]) -> None:
        self.image = image
        self.position = position


if __name__ == "__main__":
    main()
