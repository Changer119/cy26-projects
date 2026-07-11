from pathlib import Path

from auto_video_editing.models import ClipDecision, EditPlan
from auto_video_editing.subtitles import build_subtitle_events, write_srt_file


def test_build_subtitle_events_remaps_source_times_to_output_timeline() -> None:
    plan = EditPlan(
        source_video="inputs/demo.mp4",
        output_video="outputs/final.mp4",
        target_aspect="9:16",
        max_duration=60.0,
        total_duration=10.0,
        clips=[
            ClipDecision(
                source_start=10.0,
                source_end=14.0,
                output_start=0.0,
                output_end=4.0,
                text="第一段字幕",
                score=2.0,
                reason="信息密度高",
            ),
            ClipDecision(
                source_start=30.0,
                source_end=36.0,
                output_start=4.0,
                output_end=10.0,
                text="第二段字幕",
                score=2.0,
                reason="信息密度高",
            ),
        ],
    )

    events = build_subtitle_events(plan)

    assert [(event.start, event.end, event.text) for event in events] == [
        (0.0, 4.0, "第一段字幕"),
        (4.0, 10.0, "第二段字幕"),
    ]


def test_write_srt_file_renders_subtitle_events(tmp_path: Path) -> None:
    plan = EditPlan(
        source_video="inputs/demo.mp4",
        output_video="outputs/final.mp4",
        target_aspect="9:16",
        max_duration=60.0,
        total_duration=4.0,
        clips=[
            ClipDecision(
                source_start=10.0,
                source_end=14.0,
                output_start=0.0,
                output_end=4.0,
                text="第一段字幕",
                score=2.0,
                reason="信息密度高",
            )
        ],
    )

    path = write_srt_file(plan, tmp_path / "subtitles.srt")

    assert path.read_text(encoding="utf-8") == (
        "1\n"
        "00:00:00,000 --> 00:00:04,000\n"
        "第一段字幕\n\n"
    )
