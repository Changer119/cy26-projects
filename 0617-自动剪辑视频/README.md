# 自动剪辑视频工作流

这个项目用于把输入视频自动处理为 60 秒以内、9:16、带字幕的短视频。

所有运行入口都放在 `scripts/` 目录，输入素材放入 `inputs/`，输出产物写入 `outputs/`，运行日志写入 `logs/`。

## 快速开始

```bash
scripts/bootstrap.sh
scripts/run_all.sh inputs/demo.mp4
```

如果 `inputs/` 目录里只有一个视频，也可以省略路径：

```bash
scripts/run_all.sh
```

## 分步执行

```bash
scripts/run_analyze.sh inputs/demo.mp4
scripts/run_plan.sh inputs/demo.mp4
scripts/run_edit.sh
```

多段视频素材可以先生成统一分析源：

```bash
scripts/run_prepare.sh
scripts/run_analyze.sh outputs/analysis/source.mp4
scripts/run_plan.sh outputs/analysis/source.mp4
```

## 验证工作流

```bash
scripts/run_tests.sh
scripts/run_smoke.sh
```

## 关键产物

- `outputs/analysis/transcript.json`：Whisper 生成并归一化后的字幕时间轴。
- `outputs/analysis/silences.json`：ffmpeg 检测出的 0.8 秒以上静音。
- `outputs/plan.json`：正式剪辑前可审查的计划 JSON。
- `outputs/final.mp4`：最终导出的竖屏字幕短视频。

说明：如果本机 ffmpeg 支持 `subtitles` 滤镜，会烧录硬字幕；如果不支持，会自动降级为 MP4 内嵌软字幕轨。
