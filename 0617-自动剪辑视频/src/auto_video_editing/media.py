from __future__ import annotations

import logging
import re
import shutil
import subprocess
from pathlib import Path
from typing import Sequence

from auto_video_editing.media_tools.bgm import add_background_music, build_background_music_command
from auto_video_editing.media_tools.captions import burn_hard_captions
from auto_video_editing.models import AudioSlice, EditPlan
from auto_video_editing.subtitles import build_subtitle_events


SILENCE_START = re.compile(r"silence_start: (?P<start>\d+(?:\.\d+)?)")
SILENCE_END = re.compile(r"silence_end: (?P<end>\d+(?:\.\d+)?)")


def require_command(name: str) -> None:
    if shutil.which(name) is None:
        raise RuntimeError(f"缺少命令：{name}")


def extract_audio(source_video: Path, audio_path: Path, logger: logging.Logger) -> Path:
    audio_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        "ffmpeg",
        "-y",
        "-i",
        str(source_video),
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        str(audio_path),
    ]
    _run(command, logger)
    return audio_path


def detect_silences(audio_path: Path, threshold: float, logger: logging.Logger) -> list[AudioSlice]:
    command = [
        "ffmpeg",
        "-i",
        str(audio_path),
        "-af",
        f"silencedetect=noise=-35dB:d={threshold}",
        "-f",
        "null",
        "-",
    ]
    result = _run(command, logger)
    return _parse_silences(result.stderr)


def transcribe_with_whisper(audio_path: Path, output_dir: Path, model: str, language: str, logger: logging.Logger) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    command = build_whisper_command(audio_path, output_dir, model, language)
    _run(command, logger)
    return output_dir / f"{audio_path.stem}.json"


def build_whisper_command(audio_path: Path, output_dir: Path, model: str, language: str) -> list[str]:
    return [
        "uv",
        "run",
        "--python",
        "3.11",
        "--with",
        "faster-whisper",
        "auto-video-transcribe",
        str(audio_path),
        "--model",
        model,
        "--language",
        language,
        "--output_dir",
        str(output_dir),
    ]


def export_video(plan: EditPlan, subtitle_path: Path, work_dir: Path, logger: logging.Logger) -> Path:
    source = Path(plan.source_video)
    output = Path(plan.output_video)
    work_dir.mkdir(parents=True, exist_ok=True)
    output.parent.mkdir(parents=True, exist_ok=True)
    clip_paths = _render_clip_files(source, plan, work_dir, logger)
    joined_path = work_dir / "joined.mp4"
    _concat_clips(clip_paths, joined_path, work_dir / "concat.txt", logger)
    with_bgm_path = work_dir / "with_bgm.mp4"
    add_background_music(joined_path, with_bgm_path, plan.total_duration, logger)
    if ffmpeg_filter_available("subtitles", logger):
        _burn_subtitles(with_bgm_path, subtitle_path, output, logger)
    else:
        logger.warning("当前 ffmpeg 缺少 subtitles 滤镜，改用 PNG 贴图硬字幕")
        burn_hard_captions(with_bgm_path, build_subtitle_events(plan), work_dir / "captions", output, logger)
    return output


def build_vertical_video_filter() -> str:
    return "transpose=1,scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1"


def build_subtitle_filter(subtitle_path: Path) -> str:
    return f"subtitles=filename='{_escape_filter_path(subtitle_path)}'"


def ffmpeg_filter_available(filter_name: str, logger: logging.Logger) -> bool:
    result = subprocess.run(["ffmpeg", "-hide_banner", "-filters"], capture_output=True, check=False, text=True)
    if result.returncode != 0:
        logger.warning("无法读取 ffmpeg filters，按缺少 %s 处理", filter_name)
        return False
    pattern = re.compile(rf"\s{re.escape(filter_name)}\s")
    return pattern.search(result.stdout) is not None


def _render_clip_files(source: Path, plan: EditPlan, work_dir: Path, logger: logging.Logger) -> list[Path]:
    if not plan.clips:
        raise ValueError("剪辑计划里没有可导出的片段")
    clip_dir = work_dir / "clips"
    clip_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for index, clip in enumerate(plan.clips, start=1):
        path = clip_dir / f"clip_{index:03d}.mp4"
        duration = clip.source_end - clip.source_start
        command = [
            "ffmpeg",
            "-y",
            "-ss",
            f"{clip.source_start:.3f}",
            "-i",
            str(source),
            "-t",
            f"{duration:.3f}",
            "-map",
            "0:v:0",
            "-map",
            "0:a?",
            "-vf",
            build_vertical_video_filter(),
            "-r",
            "30",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "20",
            "-c:a",
            "aac",
            "-b:a",
            "160k",
            str(path),
        ]
        _run(command, logger)
        paths.append(path)
    return paths


def _concat_clips(clip_paths: list[Path], output_path: Path, concat_file: Path, logger: logging.Logger) -> None:
    concat_file.write_text(
        "\n".join(f"file '{_escape_concat_path(path)}'" for path in clip_paths) + "\n",
        encoding="utf-8",
    )
    command = [
        "ffmpeg",
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(concat_file),
        "-c",
        "copy",
        str(output_path),
    ]
    _run(command, logger)


def _burn_subtitles(input_path: Path, subtitle_path: Path, output_path: Path, logger: logging.Logger) -> None:
    command = [
        "ffmpeg",
        "-y",
        "-i",
        str(input_path),
        "-vf",
        build_subtitle_filter(subtitle_path),
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "20",
        "-c:a",
        "copy",
        str(output_path),
    ]
    _run(command, logger)


def _parse_silences(stderr: str) -> list[AudioSlice]:
    starts: list[float] = []
    slices: list[AudioSlice] = []
    for line in stderr.splitlines():
        if match := SILENCE_START.search(line):
            starts.append(float(match.group("start")))
        if match := SILENCE_END.search(line):
            start = starts.pop(0) if starts else 0.0
            slices.append(AudioSlice(start=start, end=float(match.group("end"))))
    return slices


def _run(command: Sequence[str], logger: logging.Logger, check: bool = True) -> subprocess.CompletedProcess[str]:
    logger.info("运行命令：%s", " ".join(command))
    result = subprocess.run(command, capture_output=True, check=False, text=True)
    if result.stdout:
        logger.info(result.stdout.strip())
    if result.stderr:
        logger.info(result.stderr.strip())
    if check and result.returncode != 0:
        raise RuntimeError(f"命令执行失败：{' '.join(command)}")
    return result


def _escape_concat_path(path: Path) -> str:
    return str(path).replace("'", "'\\''")


def _escape_filter_path(path: Path) -> str:
    return str(path).replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")
