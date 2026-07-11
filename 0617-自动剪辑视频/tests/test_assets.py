from pathlib import Path

from auto_video_editing.assets import build_concat_manifest, find_input_videos


def test_find_input_videos_returns_sorted_video_files(tmp_path: Path) -> None:
    (tmp_path / "b.mp4").write_text("", encoding="utf-8")
    (tmp_path / "cover.jpg").write_text("", encoding="utf-8")
    (tmp_path / "a.mov").write_text("", encoding="utf-8")

    videos = find_input_videos(tmp_path)

    assert videos == [tmp_path / "a.mov", tmp_path / "b.mp4"]


def test_build_concat_manifest_escapes_single_quotes() -> None:
    manifest = build_concat_manifest([Path("/tmp/a's.mp4"), Path("/tmp/b.mp4")])

    assert manifest == "file '/tmp/a'\\''s.mp4'\nfile '/tmp/b.mp4'\n"
