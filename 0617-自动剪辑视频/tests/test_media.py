from pathlib import Path

from auto_video_editing.media import (
    build_background_music_command,
    build_subtitle_filter,
    build_vertical_video_filter,
    build_whisper_command,
)
from auto_video_editing.media_tools.captions import CaptionImage, build_hard_caption_command


def test_build_subtitle_filter_uses_explicit_filename_option() -> None:
    filter_value = build_subtitle_filter(Path("/tmp/subtitles.ass"))

    assert filter_value == "subtitles=filename='/tmp/subtitles.ass'"


def test_build_whisper_command_uses_faster_whisper_backend() -> None:
    command = build_whisper_command(
        audio_path=Path("/tmp/audio.wav"),
        output_dir=Path("/tmp/out"),
        model="small",
        language="Chinese",
    )

    assert command[:6] == [
        "uv",
        "run",
        "--python",
        "3.11",
        "--with",
        "faster-whisper",
    ]
    assert "auto-video-transcribe" in command


def test_build_vertical_video_filter_rotates_before_cropping() -> None:
    assert build_vertical_video_filter() == (
        "transpose=1,"
        "scale=1080:1920:force_original_aspect_ratio=increase,"
        "crop=1080:1920,setsar=1"
    )


def test_build_background_music_command_mixes_low_volume_generated_bgm() -> None:
    command = build_background_music_command(
        input_path=Path("/tmp/joined.mp4"),
        output_path=Path("/tmp/with_bgm.mp4"),
        duration=12.5,
        has_source_audio=True,
    )

    assert command[:8] == [
        "ffmpeg",
        "-y",
        "-i",
        "/tmp/joined.mp4",
        "-f",
        "lavfi",
        "-t",
        "12.500",
    ]
    assert any("amix=inputs=2:duration=first:dropout_transition=2" in item for item in command)


def test_build_hard_caption_command_overlays_caption_images() -> None:
    command = build_hard_caption_command(
        input_path=Path("/tmp/with_bgm.mp4"),
        captions=[
            CaptionImage(path=Path("/tmp/caption_001.png"), start=0.0, end=2.5),
            CaptionImage(path=Path("/tmp/caption_002.png"), start=2.5, end=4.0),
        ],
        output_path=Path("/tmp/final.mp4"),
    )

    assert command[:8] == [
        "ffmpeg",
        "-y",
        "-i",
        "/tmp/with_bgm.mp4",
        "-loop",
        "1",
        "-i",
        "/tmp/caption_001.png",
    ]
    filter_value = command[command.index("-filter_complex") + 1]

    assert "[0:v][1:v]overlay=0:0:enable='between(t\\,0.000\\,2.500)'[v1]" in filter_value
    assert "[v1][2:v]overlay=0:0:enable='between(t\\,2.500\\,4.000)'[v2]" in filter_value
    assert "-shortest" in command
