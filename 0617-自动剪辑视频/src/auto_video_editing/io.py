from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Mapping, Sequence

from auto_video_editing.models import AudioSlice, ClipDecision, EditPlan, TranscriptSegment


VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v", ".mkv", ".webm"}


def ensure_project_dirs(root: Path) -> None:
    for name in ("inputs", "outputs", "logs", "scripts", "docs", "discuss"):
        (root / name).mkdir(parents=True, exist_ok=True)


def resolve_source_video(root: Path, input_value: str | None) -> Path:
    if input_value:
        path = Path(input_value)
        return path if path.is_absolute() else root / path
    videos = sorted(path for path in (root / "inputs").iterdir() if path.suffix.lower() in VIDEO_EXTENSIONS)
    if len(videos) == 1:
        return videos[0]
    if not videos:
        raise FileNotFoundError("inputs/ 目录里没有视频文件，请传入视频路径")
    raise ValueError("inputs/ 目录存在多个视频，请显式传入要处理的视频路径")


def read_transcript(path: Path) -> list[TranscriptSegment]:
    payload = _read_json(path)
    if isinstance(payload, Mapping) and isinstance(payload.get("segments"), Sequence):
        raw_segments = payload["segments"]
    elif isinstance(payload, Sequence):
        raw_segments = payload
    else:
        raise ValueError(f"无法识别字幕 JSON：{path}")
    return [_segment_from_mapping(_expect_mapping(item)) for item in raw_segments]


def write_transcript(path: Path, segments: list[TranscriptSegment]) -> Path:
    _write_json(path, {"segments": [asdict(segment) for segment in segments]})
    return path


def read_silences(path: Path) -> list[AudioSlice]:
    if not path.exists():
        return []
    payload = _read_json(path)
    if not isinstance(payload, Sequence):
        raise ValueError(f"静音 JSON 必须是数组：{path}")
    return [_slice_from_mapping(_expect_mapping(item)) for item in payload]


def write_silences(path: Path, silences: list[AudioSlice]) -> Path:
    _write_json(path, [asdict(silence) for silence in silences])
    return path


def read_edit_plan(path: Path) -> EditPlan:
    payload = _expect_mapping(_read_json(path))
    raw_clips = payload.get("clips")
    if not isinstance(raw_clips, Sequence):
        raise ValueError("剪辑计划缺少 clips 数组")
    return EditPlan(
        source_video=_read_str(payload, "source_video"),
        output_video=_read_str(payload, "output_video"),
        target_aspect=_read_str(payload, "target_aspect"),
        max_duration=_read_float(payload, "max_duration"),
        total_duration=_read_float(payload, "total_duration"),
        clips=[_clip_from_mapping(_expect_mapping(item)) for item in raw_clips],
    )


def write_edit_plan(path: Path, plan: EditPlan) -> Path:
    _write_json(path, asdict(plan))
    return path


def _read_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _expect_mapping(value: object) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError("JSON 项必须是对象")
    return value


def _segment_from_mapping(payload: Mapping[str, object]) -> TranscriptSegment:
    return TranscriptSegment(
        start=_read_float(payload, "start"),
        end=_read_float(payload, "end"),
        text=_read_str(payload, "text").strip(),
    )


def _slice_from_mapping(payload: Mapping[str, object]) -> AudioSlice:
    return AudioSlice(start=_read_float(payload, "start"), end=_read_float(payload, "end"))


def _clip_from_mapping(payload: Mapping[str, object]) -> ClipDecision:
    return ClipDecision(
        source_start=_read_float(payload, "source_start"),
        source_end=_read_float(payload, "source_end"),
        output_start=_read_float(payload, "output_start"),
        output_end=_read_float(payload, "output_end"),
        text=_read_str(payload, "text"),
        score=_read_float(payload, "score"),
        reason=_read_str(payload, "reason"),
    )


def _read_float(payload: Mapping[str, object], key: str) -> float:
    value = payload.get(key)
    if not isinstance(value, int | float):
        raise ValueError(f"字段 {key} 必须是数字")
    return float(value)


def _read_str(payload: Mapping[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str):
        raise ValueError(f"字段 {key} 必须是字符串")
    return value
