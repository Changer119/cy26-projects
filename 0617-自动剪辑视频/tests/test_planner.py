from auto_video_editing.models import AudioSlice, TranscriptSegment, WorkflowConfig
from auto_video_editing.planner import build_edit_plan


def test_build_edit_plan_excludes_long_silence_and_low_information_segments() -> None:
    segments = [
        TranscriptSegment(start=0.0, end=3.0, text="今天我们直接讲自动剪辑最关键的三个步骤"),
        TranscriptSegment(start=3.0, end=4.2, text="嗯嗯就是然后这个那个"),
        TranscriptSegment(start=4.2, end=12.0, text="第一步是先转文字，用字幕时间轴确定每一句话的位置"),
        TranscriptSegment(start=12.9, end=22.0, text="第二步是删除长停顿，并优先保留信息密度高的观点"),
        TranscriptSegment(start=23.1, end=36.0, text="第三步再把保留下来的片段合成为竖屏视频并加字幕"),
    ]
    silences = [
        AudioSlice(start=12.0, end=12.9),
        AudioSlice(start=22.0, end=23.1),
    ]
    config = WorkflowConfig(max_duration=60.0, silence_threshold=0.8, target_aspect="9:16")

    plan = build_edit_plan(
        source_video="inputs/demo.mp4",
        segments=segments,
        silences=silences,
        config=config,
    )

    assert plan.source_video == "inputs/demo.mp4"
    assert plan.target_aspect == "9:16"
    assert plan.total_duration <= 60.0
    assert [clip.text for clip in plan.clips] == [
        "今天我们直接讲自动剪辑最关键的三个步骤",
        "第一步是先转文字，用字幕时间轴确定每一句话的位置",
        "第二步是删除长停顿，并优先保留信息密度高的观点",
        "第三步再把保留下来的片段合成为竖屏视频并加字幕",
    ]
    assert all("低信息密度" not in clip.reason for clip in plan.clips)


def test_build_edit_plan_respects_max_duration_by_score_order() -> None:
    segments = [
        TranscriptSegment(start=0.0, end=20.0, text="普通介绍内容，说明背景和一些铺垫"),
        TranscriptSegment(start=20.0, end=45.0, text="关键结论：自动剪辑必须先生成可审查的剪辑计划 JSON"),
        TranscriptSegment(start=45.0, end=70.0, text="另一个关键观点：执行剪辑前要确认字幕时间轴能对齐"),
    ]
    config = WorkflowConfig(max_duration=45.0, silence_threshold=0.8, target_aspect="9:16")

    plan = build_edit_plan(
        source_video="inputs/demo.mp4",
        segments=segments,
        silences=[],
        config=config,
    )

    assert plan.total_duration <= 45.0
    assert [clip.text for clip in plan.clips] == [
        "关键结论：自动剪辑必须先生成可审查的剪辑计划 JSON",
        "另一个关键观点：执行剪辑前要确认字幕时间轴能对齐",
    ]
