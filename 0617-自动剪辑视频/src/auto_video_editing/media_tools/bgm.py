from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import Sequence


BGM_SOURCE = "aevalsrc=0.035*sin(2*PI*220*t)+0.025*sin(2*PI*277.18*t)+0.02*sin(2*PI*329.63*t):s=48000"


def add_background_music(input_path: Path, output_path: Path, duration: float, logger: logging.Logger) -> None:
    has_source_audio = _has_audio_stream(input_path, logger)
    _run(build_background_music_command(input_path, output_path, duration, has_source_audio), logger)


def build_background_music_command(
    input_path: Path,
    output_path: Path,
    duration: float,
    has_source_audio: bool,
) -> list[str]:
    duration_arg = f"{duration:.3f}"
    if has_source_audio:
        return [
            "ffmpeg",
            "-y",
            "-i",
            str(input_path),
            "-f",
            "lavfi",
            "-t",
            duration_arg,
            "-i",
            BGM_SOURCE,
            "-filter_complex",
            "[0:a]volume=1.0[a0];[1:a]volume=0.12[bg];[a0][bg]amix=inputs=2:duration=first:dropout_transition=2[a]",
            "-map",
            "0:v:0",
            "-map",
            "[a]",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "160k",
            str(output_path),
        ]
    return [
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-t",
        duration_arg,
        "-i",
        BGM_SOURCE,
        "-i",
        str(input_path),
        "-map",
        "1:v:0",
        "-map",
        "0:a:0",
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-b:a",
        "160k",
        "-shortest",
        str(output_path),
    ]


def _has_audio_stream(path: Path, logger: logging.Logger) -> bool:
    command = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "a:0",
        "-show_entries",
        "stream=index",
        "-of",
        "csv=p=0",
        str(path),
    ]
    result = subprocess.run(command, capture_output=True, check=False, text=True)
    if result.returncode != 0:
        logger.warning("无法检测音频流，按无源音频处理：%s", path)
        return False
    return bool(result.stdout.strip())


def _run(command: Sequence[str], logger: logging.Logger) -> None:
    logger.info("运行命令：%s", " ".join(command))
    result = subprocess.run(command, capture_output=True, check=False, text=True)
    if result.stdout:
        logger.info(result.stdout.strip())
    if result.stderr:
        logger.info(result.stderr.strip())
    if result.returncode != 0:
        raise RuntimeError(f"命令执行失败：{' '.join(command)}")
