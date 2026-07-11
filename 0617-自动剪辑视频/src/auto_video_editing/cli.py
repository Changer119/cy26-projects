from __future__ import annotations

import argparse
import logging
from pathlib import Path

from auto_video_editing.assets import prepare_source_video
from auto_video_editing.io import (
    ensure_project_dirs,
    read_edit_plan,
    read_silences,
    read_transcript,
    resolve_source_video,
    write_edit_plan,
    write_silences,
    write_transcript,
)
from auto_video_editing.media import detect_silences, export_video, extract_audio, require_command, transcribe_with_whisper
from auto_video_editing.models import TranscriptSegment, WorkflowConfig
from auto_video_editing.planner import build_edit_plan
from auto_video_editing.subtitles import write_ass_file


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()
    root = Path.cwd()
    ensure_project_dirs(root)
    logger = _setup_logger(root, args.command)
    args.handler(root, args, logger)


def transcribe_main() -> None:
    parser = argparse.ArgumentParser(description="使用 faster-whisper 生成 Whisper 字幕 JSON")
    parser.add_argument("audio_path")
    parser.add_argument("--model", default="small")
    parser.add_argument("--language", default="Chinese")
    parser.add_argument("--output_dir", required=True)
    args = parser.parse_args()
    audio_path = Path(args.audio_path)
    segments = _transcribe_with_faster_whisper(audio_path, args.model, args.language)
    write_transcript(Path(args.output_dir) / f"{audio_path.stem}.json", segments)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="自动剪辑视频工作流")
    subparsers = parser.add_subparsers(dest="command", required=True)

    doctor = subparsers.add_parser("doctor", help="检查本地工具和目录")
    doctor.set_defaults(handler=_doctor)

    prepare = subparsers.add_parser("prepare", help="把 inputs/ 中的视频合并为分析源")
    prepare.set_defaults(handler=_prepare)

    analyze = subparsers.add_parser("analyze", help="提取音频、检测静音、Whisper 转文字")
    analyze.add_argument("--input", dest="input_video")
    analyze.add_argument("--model", default="small")
    analyze.add_argument("--language", default="Chinese")
    analyze.set_defaults(handler=_analyze)

    plan = subparsers.add_parser("plan", help="生成剪辑计划 JSON")
    plan.add_argument("--input", dest="input_video")
    plan.add_argument("--max-duration", type=float, default=60.0)
    plan.add_argument("--silence-threshold", type=float, default=0.8)
    plan.set_defaults(handler=_plan)

    edit = subparsers.add_parser("edit", help="按剪辑计划导出成片")
    edit.add_argument("--plan", default="outputs/plan.json")
    edit.set_defaults(handler=_edit)

    run_all = subparsers.add_parser("all", help="依次执行 analyze、plan、edit")
    run_all.add_argument("--input", dest="input_video")
    run_all.add_argument("--model", default="small")
    run_all.add_argument("--language", default="Chinese")
    run_all.add_argument("--max-duration", type=float, default=60.0)
    run_all.add_argument("--silence-threshold", type=float, default=0.8)
    run_all.set_defaults(handler=_all)
    return parser


def _doctor(root: Path, args: argparse.Namespace, logger: logging.Logger) -> None:
    del args
    require_command("uv")
    require_command("ffmpeg")
    require_command("ffprobe")
    ensure_project_dirs(root)
    logger.info("环境检查通过")
    print("环境检查通过：uv、ffmpeg、ffprobe 可用，项目目录已就绪")


def _prepare(root: Path, args: argparse.Namespace, logger: logging.Logger) -> None:
    del args
    require_command("ffmpeg")
    source_path = prepare_source_video(root / "inputs", root / "outputs" / "analysis" / "source.mp4", logger)
    print(f"分析源已生成：{source_path}")


def _analyze(root: Path, args: argparse.Namespace, logger: logging.Logger) -> None:
    source_video = resolve_source_video(root, args.input_video)
    transcript_path = _run_analyze(root, source_video, args.model, args.language, logger)
    print(f"分析完成：{transcript_path}")


def _plan(root: Path, args: argparse.Namespace, logger: logging.Logger) -> None:
    source_video = resolve_source_video(root, args.input_video)
    plan_path = _run_plan(root, source_video, args.max_duration, args.silence_threshold, logger)
    print(f"剪辑计划已生成：{plan_path}")


def _edit(root: Path, args: argparse.Namespace, logger: logging.Logger) -> None:
    output_path = _run_edit(root, Path(args.plan), logger)
    print(f"成片已导出：{output_path}")


def _all(root: Path, args: argparse.Namespace, logger: logging.Logger) -> None:
    source_video = resolve_source_video(root, args.input_video)
    _run_analyze(root, source_video, args.model, args.language, logger)
    _run_plan(root, source_video, args.max_duration, args.silence_threshold, logger)
    output_path = _run_edit(root, root / "outputs" / "plan.json", logger)
    print(f"完整流程完成：{output_path}")


def _run_analyze(root: Path, source_video: Path, model: str, language: str, logger: logging.Logger) -> Path:
    require_command("uv")
    require_command("ffmpeg")
    analysis_dir = root / "outputs" / "analysis"
    audio_path = analysis_dir / "audio.wav"
    extract_audio(source_video, audio_path, logger)
    silences = detect_silences(audio_path, 0.8, logger)
    write_silences(analysis_dir / "silences.json", silences)
    raw_transcript_path = transcribe_with_whisper(audio_path, analysis_dir, model, language, logger)
    segments = read_transcript(raw_transcript_path)
    transcript_path = analysis_dir / "transcript.json"
    write_transcript(transcript_path, segments)
    return transcript_path


def _run_plan(
    root: Path,
    source_video: Path,
    max_duration: float,
    silence_threshold: float,
    logger: logging.Logger,
) -> Path:
    del logger
    analysis_dir = root / "outputs" / "analysis"
    segments = read_transcript(analysis_dir / "transcript.json")
    silences = read_silences(analysis_dir / "silences.json")
    config = WorkflowConfig(max_duration=max_duration, silence_threshold=silence_threshold, target_aspect="9:16")
    plan = build_edit_plan(
        source_video=str(source_video),
        output_video=str(root / "outputs" / "final.mp4"),
        segments=segments,
        silences=silences,
        config=config,
    )
    plan_path = root / "outputs" / "plan.json"
    write_edit_plan(plan_path, plan)
    return plan_path


def _run_edit(root: Path, plan_path: Path, logger: logging.Logger) -> Path:
    require_command("ffmpeg")
    plan = read_edit_plan(plan_path if plan_path.is_absolute() else root / plan_path)
    work_dir = root / "outputs" / "work"
    subtitle_path = write_ass_file(plan, work_dir / "subtitles.ass")
    return export_video(plan, subtitle_path, work_dir, logger)


def _setup_logger(root: Path, command: str) -> logging.Logger:
    log_dir = root / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("auto_video_editing")
    logger.handlers.clear()
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    file_handler = logging.FileHandler(log_dir / f"{command}.log", encoding="utf-8")
    file_handler.setFormatter(formatter)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
    return logger


def _transcribe_with_faster_whisper(audio_path: Path, model: str, language: str) -> list[TranscriptSegment]:
    from faster_whisper import WhisperModel

    whisper = WhisperModel(model, device="cpu", compute_type="int8")
    raw_segments, _info = whisper.transcribe(
        str(audio_path),
        language=_normalize_language(language),
        vad_filter=True,
        beam_size=5,
    )
    segments: list[TranscriptSegment] = []
    for segment in raw_segments:
        text = segment.text.strip()
        if text and segment.end > segment.start:
            segments.append(TranscriptSegment(start=float(segment.start), end=float(segment.end), text=text))
    return segments


def _normalize_language(language: str) -> str:
    lowered = language.lower()
    if lowered in {"chinese", "zh", "zh-cn", "cn"}:
        return "zh"
    return lowered
