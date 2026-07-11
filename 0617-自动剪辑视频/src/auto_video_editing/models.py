from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TranscriptSegment:
    start: float
    end: float
    text: str

    def __post_init__(self) -> None:
        if self.start < 0:
            raise ValueError("字幕开始时间不能小于 0")
        if self.end <= self.start:
            raise ValueError("字幕结束时间必须大于开始时间")
        if not self.text.strip():
            raise ValueError("字幕文本不能为空")

    @property
    def duration(self) -> float:
        return self.end - self.start


@dataclass(frozen=True)
class AudioSlice:
    start: float
    end: float

    def __post_init__(self) -> None:
        if self.start < 0:
            raise ValueError("音频片段开始时间不能小于 0")
        if self.end <= self.start:
            raise ValueError("音频片段结束时间必须大于开始时间")

    @property
    def duration(self) -> float:
        return self.end - self.start


@dataclass(frozen=True)
class WorkflowConfig:
    max_duration: float = 60.0
    silence_threshold: float = 0.8
    target_aspect: str = "9:16"
    min_information_score: float = 0.8
    min_clip_duration: float = 1.0

    def __post_init__(self) -> None:
        if self.max_duration <= 0:
            raise ValueError("最大时长必须大于 0")
        if self.silence_threshold < 0:
            raise ValueError("静音阈值不能小于 0")
        if self.target_aspect != "9:16":
            raise ValueError("当前工作流只支持 9:16 输出")
        if self.min_clip_duration <= 0:
            raise ValueError("最小片段时长必须大于 0")


@dataclass(frozen=True)
class ClipDecision:
    source_start: float
    source_end: float
    output_start: float
    output_end: float
    text: str
    score: float
    reason: str

    def __post_init__(self) -> None:
        if self.source_end <= self.source_start:
            raise ValueError("源片段结束时间必须大于开始时间")
        if self.output_end <= self.output_start:
            raise ValueError("输出片段结束时间必须大于开始时间")
        if not self.text.strip():
            raise ValueError("片段文本不能为空")

    @property
    def duration(self) -> float:
        return self.source_end - self.source_start


@dataclass(frozen=True)
class EditPlan:
    source_video: str
    output_video: str
    target_aspect: str
    max_duration: float
    total_duration: float
    clips: list[ClipDecision]


@dataclass(frozen=True)
class SubtitleEvent:
    start: float
    end: float
    text: str
