# Qwen3-ASR 0.6B 离线引擎

## 配置与使用

在托盘的 ASR 引擎菜单选择「Qwen3-ASR 0.6B (离线)」。模型未安装时会打开初始化向导，自动下载识别模型和 Silero VAD，也可按照手动安装指南放置文件。新安装默认使用 Qwen3-ASR；已有配置文件中的 `engine` 设置保持不变。

在 `~/.config/nextalk/settings.yaml` 中设置以下字段，修改参数后重启应用；设置了 `XDG_CONFIG_HOME` 时使用对应目录。托盘选择的引擎会同步保存到配置文件。

```yaml
model:
  engine: qwen3_asr
  qwen3_asr:
    num_threads: 2
    max_new_tokens: 128
    hotwords: "Nextalk,语音输入"
    custom_url: ""
```

`num_threads` 支持 1–256，`max_new_tokens` 支持 1–512，非法值退回默认值。热词用英文逗号分隔。固定默认值与官方配置一致：`max_total_len=512`、`temperature=0.000001`（近零温度，贪心选择）、`top_p=0.8`、`seed=42`。音频为 16 kHz；Silero VAD 窗口 512 点，最长 10 秒分段。发话结束会刷新 VAD、识别尾段，再清空会话状态。

## 模型来源与完整性

已实际下载并核对[官方模型包](https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-qwen3-asr-0.6B-int8-2026-03-25.tar.bz2)，压缩包为 878702423 字节，SHA256 与 GitHub 发布附件元数据一致：

```text
393f8a14e2f5fb96746aaab342997a40641001fbd5bf9592a080a8329178ee96
```

模型目录为 `$XDG_DATA_HOME/nextalk/models/qwen3_asr/`；未设置环境变量时为 `~/.local/share/nextalk/models/qwen3_asr/`。需要以下六个非空文件，约占 942 MiB，不需要 `tokens.txt`：

```text
qwen3_asr/
  conv_frontend.onnx
  encoder.int8.onnx
  decoder.int8.onnx
  tokenizer/vocab.json
  tokenizer/merges.txt
  tokenizer/tokenizer_config.json
```

[Silero VAD](https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/silero_vad.onnx) 放在相邻的 `vad/silero_vad.onnx`，实测 SHA256：

```text
9e2449e1087496d8d4caba907f23e0bd3f78d91fa552479bb9c23ac09cbb1fd6
```

自动下载先验证压缩包 SHA256，再通过系统 `tar`/`bzip2` 在临时目录解压六个必需文件；文件检查通过才替换目标目录。解压失败保留现有模型。VAD 下载到 `.part` 文件，校验通过后才安装，避免中断下载被当作可用模型。自定义下载 URL 仍须提供相同官方模型包，不能绕过校验。手动安装与启动检查验证文件存在且非空，不对已安装的大模型逐次重算 SHA256。

## 原生库与 ABI

原生库升级为 [sherpa-onnx v2.0.1](https://github.com/k2-fsa/sherpa-onnx/releases/tag/v2.0.1)，这是核验日 2026-10-31 GitHub 最新稳定版；随包 ONNX Runtime 为 1.28.2。来源及两个动态库的 SHA256 见 [VERSIONS.md](../libs/VERSIONS.md)。构建产物中两个动态库与仓库文件的 SHA256 一致。

以该标签的 [c-api.h](https://github.com/k2-fsa/sherpa-onnx/blob/v2.0.1/sherpa-onnx/c-api/c-api.h) 为依据，逐字段核对三个绑定文件的 39 个结构体、192 个字段的顺序及类型，保留既有 Dart 字段命名。修正包括：

- Whisper 的两个时间戳开关、Moonshine 的 `merged_decoder`。
- `omnilingual` 后的 MedASR、FunASR Nano、FireRedASR CTC、Qwen3-ASR、Cohere Transcribe 全部字段。
- 离线识别器末尾的 `ctc_fst_decoder_config` 和离线结果的分段字段。
- `SherpaOnnxSpeechSegment.start` 改为 `Int64`。
- 在线识别器、在线模型和 VAD 配置均已核对，新版无额外缺失字段。

测试期望值由 C 编译器的 `sizeof` 和 `offsetof` 实测得出。Linux x64 下离线模型配置为 504 字节，离线识别器配置为 624 字节，在线识别器配置为 272 字节，VAD 配置为 88 字节。新增测试还覆盖关键字段偏移与超过 32 位的 VAD 起点。

## 验证记录

阶段一在接入新引擎之前完成：原有全量测试 802 项通过、6 项跳过；新增 39 个结构体大小校验的测试单独通过；`flutter build linux` 成功。

阶段二最终验证：在 `voice_capsule/` 执行 `flutter test`，816 项通过、6 项跳过；`flutter build linux` 成功，`git diff --check` 通过。单元测试覆盖模型缺失及空文件、配置默认值及越界值、参数从 YAML 传入运行配置、三引擎回退、解压失败保留原模型、下载校验失败以及 ABI 布局。

本机原 Flutter SDK 目录只读，因此将同一 SDK 复制到 `/tmp/nextalk-flutter` 后运行。构建产物为 `voice_capsule/build/linux/x64/release/bundle/voice_capsule`。

真实识别验证使用仓库 Dart FFI、新 Qwen3-ASR 引擎和 Silero VAD，CPU 为 Intel Core i9-14900KF，推理线程数为 2。每个样例在同一引擎上连续识别两次，验证非空结果、两次结果一致和收尾后的状态清理：

| 样例 | 音频时长 | 初始化 | 第一次识别 | 第二次识别 |
|---|---:|---:|---:|---:|
| `fr1.wav` | 5.996 秒 | 2.549 秒 | 1.565 秒 | 2.122 秒 |
| `codeswitch.wav`，重采样到 16 kHz | 6.230 秒 | 2.759 秒 | 1.407 秒 | 1.657 秒 |
| `noise2.wav` | 22.833 秒 | 6.275 秒 | 15.178 秒 | 8.470 秒 |

法语输出为 `Annie et moi sommes allés à Paris voyager en train au printemps, c'était très amusant.`。中文带噪样例识别出了号码和「纠正，纠正，不是九六」等内容。计时包含全部 VAD 分段推理及尾段刷新，不包含初始化；部分验证与分析工具并行运行，这些数值只用于本机链路验证。

复现命令（在 `voice_capsule/` 目录运行）：

```bash
LD_LIBRARY_PATH="$PWD/../libs" dart run tool/qwen3_asr_smoke.dart \
  /tmp/sherpa-onnx-qwen3-asr-0.6B-int8-2026-03-25 \
  /tmp/nextalk-silero_vad.onnx \
  /tmp/sherpa-onnx-qwen3-asr-0.6B-int8-2026-03-25/test_wavs/fr1.wav
```

模型和样例已下载到上述临时目录，没有安装到用户模型目录，也没有修改用户设置。

## 限制与风险

- 未做 Linux 桌面托盘/向导的人工点击验收；已完成代码接入、单元测试和 Linux 构建。
- 实测存在误识别：法语人名 Alice 被识别为 Annie，多语切换样例中的其他语言被误转成英文，中文噪声片段出现额外文本。这些测试确认识别链路和会话隔离，不代表准确率达标。
- 离线推理会等待 VAD 分段结束；沿用现有同步识别接口，较长或复杂语音会增加界面等待时间。达到生成 token 上限时可能截断，可调整 `max_new_tokens`。
- 自动解压依赖系统 `tar` 和 `bzip2`。安装时压缩包与解压目录同时存在，需要约 1.8 GiB 以上可用磁盘空间；替换现有模型时还需要保留旧模型的空间。
- 6 项现有测试按其环境条件跳过；真实模型验证由独立烟雾脚本补充。没有创建 git commit，原有 `.claude/settings.local.json` 改动未触碰。

## 修改文件清单

共 35 个文件（不含用户原有改动）：

- `docs/qwen3-asr.md`
- `libs/VERSIONS.md`
- `libs/libonnxruntime.so`
- `libs/libsherpa-onnx-c-api.so`
- `voice_capsule/lib/constants/qwen3_asr_constants.dart`
- `voice_capsule/lib/constants/settings_constants.dart`
- `voice_capsule/lib/ffi/sherpa_offline_bindings.dart`
- `voice_capsule/lib/ffi/sherpa_onnx_bindings.dart`
- `voice_capsule/lib/ffi/sherpa_vad_bindings.dart`
- `voice_capsule/lib/l10n/app_en.arb`
- `voice_capsule/lib/l10n/app_localizations.dart`
- `voice_capsule/lib/l10n/app_localizations_en.dart`
- `voice_capsule/lib/l10n/app_localizations_zh.dart`
- `voice_capsule/lib/l10n/app_zh.arb`
- `voice_capsule/lib/main.dart`
- `voice_capsule/lib/services/asr/asr_engine.dart`
- `voice_capsule/lib/services/asr/asr_engine_factory.dart`
- `voice_capsule/lib/services/asr/engine_initializer.dart`
- `voice_capsule/lib/services/asr/qwen3_asr_engine.dart`
- `voice_capsule/lib/services/audio_inference_pipeline.dart`
- `voice_capsule/lib/services/language_service.dart`
- `voice_capsule/lib/services/model_manager.dart`
- `voice_capsule/lib/services/settings_service.dart`
- `voice_capsule/lib/services/tray_service.dart`
- `voice_capsule/lib/ui/init_wizard/init_wizard.dart`
- `voice_capsule/lib/ui/init_wizard/manual_install_guide.dart`
- `voice_capsule/test/ffi/sherpa_abi_layout_test.dart`
- `voice_capsule/test/services/asr/asr_engine_test.dart`
- `voice_capsule/test/services/asr/engine_initializer_test.dart`
- `voice_capsule/test/services/asr/qwen3_asr_engine_test.dart`
- `voice_capsule/test/services/model_manager_test.dart`
- `voice_capsule/test/services/qwen3_asr_settings_test.dart`
- `voice_capsule/test/services/settings_service_test.dart`
- `voice_capsule/test/services/tray_service_test.dart`
- `voice_capsule/tool/qwen3_asr_smoke.dart`
