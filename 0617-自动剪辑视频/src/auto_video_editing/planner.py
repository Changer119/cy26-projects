from __future__ import annotations

import re
from dataclasses import dataclass

from auto_video_editing.models import AudioSlice, ClipDecision, EditPlan, TranscriptSegment, WorkflowConfig


FILLER_WORDS = (
    "嗯",
    "啊",
    "呃",
    "就是",
    "然后",
    "这个",
    "那个",
    "其实",
    "可能",
    "大概",
    "额",
)

KEYWORDS = (
    "关键",
    "结论",
    "必须",
    "步骤",
    "方法",
    "问题",
    "原因",
    "第一",
    "第二",
    "第三",
    "重点",
    "JSON",
    "自动剪辑",
)

PUNCTUATION = re.compile(r"[\s，。！？、,.!?：:；;（）()\[\]【】《》\"'“”‘’]+")


@dataclass(frozen=True)
class CandidateClip:
    segment: TranscriptSegment
    score: float
    reason: str


def build_edit_plan(
    source_video: str,
    segments: list[TranscriptSegment],
    silences: list[AudioSlice],
    config: WorkflowConfig,
    output_video: str = "outputs/final.mp4",
) -> EditPlan:
    candidates = [
        candidate
        for segment in segments
        if (candidate := _build_candidate(segment, silences, config)) is not None
    ]
    chosen = _choose_candidates(candidates, config)
    clips = _build_output_timeline(chosen, config)
    total_duration = round(sum(clip.duration for clip in clips), 3)
    return EditPlan(
        source_video=source_video,
        output_video=output_video,
        target_aspect=config.target_aspect,
        max_duration=config.max_duration,
        total_duration=total_duration,
        clips=clips,
    )


def _build_candidate(
    segment: TranscriptSegment,
    silences: list[AudioSlice],
    config: WorkflowConfig,
) -> CandidateClip | None:
    if _long_silence_overlap(segment, silences, config.silence_threshold) >= segment.duration * 0.6:
        return None
    score = information_score(segment)
    if score < config.min_information_score:
        return None
    reason = f"信息密度 {score:.2f}，长静音会在拼接时压缩"
    return CandidateClip(segment=segment, score=score, reason=reason)


def information_score(segment: TranscriptSegment) -> float:
    cleaned = _remove_fillers(PUNCTUATION.sub("", segment.text))
    if not cleaned:
        return 0.0
    density = len(cleaned) / max(segment.duration, 0.1)
    keyword_boost = sum(0.6 for keyword in KEYWORDS if keyword in segment.text)
    return round(density + keyword_boost, 3)


def _remove_fillers(text: str) -> str:
    cleaned = text
    for word in FILLER_WORDS:
        cleaned = cleaned.replace(word, "")
    return cleaned


def _long_silence_overlap(segment: TranscriptSegment, silences: list[AudioSlice], threshold: float) -> float:
    overlap = 0.0
    for silence in silences:
        if silence.duration < threshold:
            continue
        start = max(segment.start, silence.start)
        end = min(segment.end, silence.end)
        if end > start:
            overlap += end - start
    return overlap


def _choose_candidates(candidates: list[CandidateClip], config: WorkflowConfig) -> list[CandidateClip]:
    ordered = sorted(candidates, key=lambda item: (-item.score, item.segment.start))
    chosen: list[CandidateClip] = []
    remaining = config.max_duration
    for candidate in ordered:
        if remaining < config.min_clip_duration:
            break
        usable_duration = min(candidate.segment.duration, remaining)
        if usable_duration >= config.min_clip_duration:
            chosen.append(candidate)
            remaining -= usable_duration
    return sorted(chosen, key=lambda item: item.segment.start)


def _build_output_timeline(candidates: list[CandidateClip], config: WorkflowConfig) -> list[ClipDecision]:
    clips: list[ClipDecision] = []
    cursor = 0.0
    remaining = config.max_duration
    for candidate in candidates:
        duration = min(candidate.segment.duration, remaining)
        if duration < config.min_clip_duration:
            break
        source_end = candidate.segment.start + duration
        reason = candidate.reason
        if duration < candidate.segment.duration:
            reason = f"{reason}，为满足总时长裁剪"
        clips.append(
            ClipDecision(
                source_start=round(candidate.segment.start, 3),
                source_end=round(source_end, 3),
                output_start=round(cursor, 3),
                output_end=round(cursor + duration, 3),
                text=candidate.segment.text.strip(),
                score=candidate.score,
                reason=reason,
            )
        )
        cursor += duration
        remaining -= duration
    return clips
