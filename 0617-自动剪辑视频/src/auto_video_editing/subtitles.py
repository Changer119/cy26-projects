from __future__ import annotations

from pathlib import Path

from auto_video_editing.models import EditPlan, SubtitleEvent


def build_subtitle_events(plan: EditPlan) -> list[SubtitleEvent]:
    return [
        SubtitleEvent(start=clip.output_start, end=clip.output_end, text=clip.text)
        for clip in plan.clips
    ]


def write_ass_file(plan: EditPlan, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    events = build_subtitle_events(plan)
    output_path.write_text(_render_ass(events), encoding="utf-8")
    return output_path


def write_srt_file(plan: EditPlan, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    events = build_subtitle_events(plan)
    output_path.write_text(_render_srt(events), encoding="utf-8")
    return output_path


def _render_ass(events: list[SubtitleEvent]) -> str:
    lines = [
        "[Script Info]",
        "ScriptType: v4.00+",
        "PlayResX: 1080",
        "PlayResY: 1920",
        "WrapStyle: 0",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
        "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, "
        "Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        "Style: Default,Arial,64,&H00FFFFFF,&H00FFFFFF,&H00111111,&HAA000000,"
        "1,0,0,0,100,100,0,0,1,4,1,2,80,80,210,1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    for event in events:
        lines.append(
            "Dialogue: 0,"
            f"{_format_ass_time(event.start)},{_format_ass_time(event.end)},"
            f"Default,,0,0,0,,{_escape_ass_text(event.text)}"
        )
    return "\n".join(lines) + "\n"


def _format_ass_time(seconds: float) -> str:
    centiseconds = int(round(seconds * 100))
    hours, remainder = divmod(centiseconds, 360_000)
    minutes, remainder = divmod(remainder, 6_000)
    secs, centis = divmod(remainder, 100)
    return f"{hours}:{minutes:02d}:{secs:02d}.{centis:02d}"


def _render_srt(events: list[SubtitleEvent]) -> str:
    blocks: list[str] = []
    for index, event in enumerate(events, start=1):
        blocks.append(
            f"{index}\n"
            f"{_format_srt_time(event.start)} --> {_format_srt_time(event.end)}\n"
            f"{event.text}\n"
        )
    return "\n".join(blocks) + ("\n" if blocks else "")


def _format_srt_time(seconds: float) -> str:
    milliseconds = int(round(seconds * 1000))
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, millis = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def _escape_ass_text(text: str) -> str:
    return text.replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}").replace("\n", "\\N")
