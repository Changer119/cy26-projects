from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import Sequence

from auto_video_editing.io import VIDEO_EXTENSIONS


def find_input_videos(input_dir: Path) -> list[Path]:
    return sorted(path for path in input_dir.iterdir() if path.is_file() and path.suffix.lower() in VIDEO_EXTENSIONS)


def build_concat_manifest(video_paths: Sequence[Path]) -> str:
    return "".join(f"file '{_escape_concat_path(path)}'\n" for path in video_paths)


def prepare_source_video(input_dir: Path, output_path: Path, logger: logging.Logger) -> Path:
    videos = find_input_videos(input_dir)
    if not videos:
        raise FileNotFoundError(f"{input_dir} 中没有可合并的视频素材")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path = output_path.parent / "source_concat.txt"
    manifest_path.write_text(build_concat_manifest(videos), encoding="utf-8")
    command = [
        "ffmpeg",
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(manifest_path),
        "-map",
        "0:v:0",
        "-map",
        "0:a?",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "18",
        "-c:a",
        "aac",
        "-b:a",
        "160k",
        "-movflags",
        "+faststart",
        str(output_path),
    ]
    _run(command, logger)
    return output_path


def _escape_concat_path(path: Path) -> str:
    return str(path).replace("'", "'\\''")


def _run(command: Sequence[str], logger: logging.Logger) -> None:
    logger.info("运行命令：%s", " ".join(command))
    result = subprocess.run(command, capture_output=True, check=False, text=True)
    if result.stdout:
        logger.info(result.stdout.strip())
    if result.stderr:
        logger.info(result.stderr.strip())
    if result.returncode != 0:
        raise RuntimeError(f"命令执行失败：{' '.join(command)}")
