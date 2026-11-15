# Nextalk Flutter 客户端

`voice_capsule` 是 Nextalk 的 Linux 桌面客户端，负责音频采集、语音识别、胶囊窗口、统一设置窗口及文本上屏编排。支持 Qwen3-ASR（默认）、SenseVoice、Zipformer 本地引擎和 DeepSeek 云端引擎。

从仓库根目录运行：

```bash
make deps
make test
make analyze
make run
```

正式发布通过根目录 `scripts/release.sh` 触发 GitHub Actions，在 Docker 中构建客户端和 Fcitx5 插件，再生成 DEB/RPM。发布镜像使用 Flutter 3.32.5，新增 UI API 需兼容该版本；本地较新 SDK 的测试通过不代表发布镜像能够编译。

- [安装与使用](../README_zh.md)
- [DeepSeek 配置与录音行为](../docs/deepseek-asr.md)
- [架构说明](../docs/architecture_zh.md)
- [构建与发布流程](../docs/build-and-release_zh.md)
- [更新日志](../CHANGELOG.md)
