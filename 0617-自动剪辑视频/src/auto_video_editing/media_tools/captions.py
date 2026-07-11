from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from PIL import Image, ImageDraw, ImageFont

from auto_video_editing.models import SubtitleEvent


CANVAS_SIZE = (1080, 1920)
FONT_SIZE = 76
MAX_TEXT_WIDTH = 920
CAPTION_Y = 1450
FONT_CANDIDATES = [
    Path("/System/Library/Fonts/PingFang.ttc"),
    Path("/System/Library/Fonts/STHeiti Light.ttc"),
    Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf"),
    Path("/Library/Fonts/Arial Unicode.ttf"),
]


@dataclass(frozen=True)
class CaptionImage:
    path: Path
    start: float
    end: float


def burn_hard_captions(
    input_path: Path,
    events: list[SubtitleEvent],
    image_dir: Path,
    output_path: Path,
    logger: logging.Logger,
) -> None:
    captions = render_caption_images(events, image_dir)
    _run(build_hard_caption_command(input_path, captions, output_path), logger)


def render_caption_images(events: list[SubtitleEvent], output_dir: Path) -> list[CaptionImage]:
    output_dir.mkdir(parents=True, exist_ok=True)
    font = _load_caption_font()
    captions: list[CaptionImage] = []
    for index, event in enumerate(events, start=1):
        path = output_dir / f"caption_{index:03d}.png"
        _render_single_caption(event.text, font, path)
        captions.append(CaptionImage(path=path, start=event.start, end=event.end))
    return captions


def build_hard_caption_command(input_path: Path, captions: list[CaptionImage], output_path: Path) -> list[str]:
    if not captions:
        return ["ffmpeg", "-y", "-i", str(input_path), "-c", "copy", str(output_path)]
    command = ["ffmpeg", "-y", "-i", str(input_path)]
    for caption in captions:
        command.extend(["-loop", "1", "-i", str(caption.path)])
    command.extend(
        [
            "-filter_complex",
            _build_overlay_filter(captions),
            "-map",
            f"[v{len(captions)}]",
            "-map",
            "0:a?",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "20",
            "-c:a",
            "copy",
            "-shortest",
            str(output_path),
        ]
    )
    return command


def _render_single_caption(text: str, font: ImageFont.ImageFont, path: Path) -> None:
    image = Image.new("RGBA", CANVAS_SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    wrapped_text = _wrap_text(text, font, draw)
    box = draw.multiline_textbbox((0, 0), wrapped_text, font=font, spacing=12, stroke_width=4)
    text_width = box[2] - box[0]
    text_height = box[3] - box[1]
    x = (CANVAS_SIZE[0] - text_width) // 2
    y = CAPTION_Y
    padding_x = 44
    padding_y = 28
    rect = (
        x - padding_x,
        y - padding_y,
        x + text_width + padding_x,
        y + text_height + padding_y,
    )
    draw.rounded_rectangle(rect, radius=28, fill=(0, 0, 0, 145))
    draw.multiline_text(
        (x, y),
        wrapped_text,
        font=font,
        fill=(255, 255, 255, 255),
        spacing=12,
        stroke_width=4,
        stroke_fill=(0, 0, 0, 255),
    )
    image.save(path)


def _wrap_text(text: str, font: ImageFont.ImageFont, draw: ImageDraw.ImageDraw) -> str:
    lines: list[str] = []
    current = ""
    for char in text.strip():
        candidate = current + char
        width = draw.textbbox((0, 0), candidate, font=font, stroke_width=4)[2]
        if width <= MAX_TEXT_WIDTH or not current:
            current = candidate
            continue
        lines.append(current)
        current = char
    if current:
        lines.append(current)
    return "\n".join(lines[:2])


def _build_overlay_filter(captions: list[CaptionImage]) -> str:
    parts: list[str] = []
    previous = "[0:v]"
    for index, caption in enumerate(captions, start=1):
        output = f"[v{index}]"
        enable = f"between(t\\,{caption.start:.3f}\\,{caption.end:.3f})"
        parts.append(f"{previous}[{index}:v]overlay=0:0:enable='{enable}'{output}")
        previous = output
    return ";".join(parts)


def _load_caption_font() -> ImageFont.ImageFont:
    for path in FONT_CANDIDATES:
        if path.exists():
            return ImageFont.truetype(str(path), FONT_SIZE)
    return ImageFont.load_default(size=FONT_SIZE)


def _run(command: Sequence[str], logger: logging.Logger) -> None:
    logger.info("运行命令：%s", " ".join(command))
    result = subprocess.run(command, capture_output=True, check=False, text=True)
    if result.stdout:
        logger.info(result.stdout.strip())
    if result.stderr:
        logger.info(result.stderr.strip())
    if result.returncode != 0:
        raise RuntimeError(f"命令执行失败：{' '.join(command)}")
