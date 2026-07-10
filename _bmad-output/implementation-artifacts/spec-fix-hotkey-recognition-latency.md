---
title: '修复快捷键后语音识别迟滞回归（PulseAudio 缓冲 + 预热失效）'
type: 'bugfix'
created: '2026-07-09'
status: 'done'
baseline_commit: e1af20e5bcc9f0c6e1925747e8c6ed597a2e6513
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** 升级后按快捷键说话不能及时识别，需反复按键，上一段内容延迟到下一次才显示。两个根因（0.2.6–0.2.8 音频重构/延迟优化引入，与 Story 3-10 Portal 无关——安装包实际不含 Portal 代码）：
1. `pa_simple_new` 缓冲属性传 nullptr，录音流用服务端默认 fragsize（可达秒级），音频成批迟到；`pa_simple_read` 又在主 isolate 同步阻塞，碎片未到时 UI 冻结，诱发用户反复按键掐断录音。
2. ASR 预初始化用遗留模型路径 `modelManager.modelPath`（目录已不存在），每次启动 `modelNotFound`，预热从未生效，首次录音才加载几百 MB 模型。

**Approach:** 录音流显式配置 fragsize=100ms 的缓冲属性；预初始化改用正确路径并与管线共用同一配置构造；模型/引擎切换后重新预热。

## Boundaries & Constraints

**Always:**
- fragsize = 1600 样本 × 4 字节 = 6400 bytes（与 `framesPerBuffer` 100ms 对齐）
- 预初始化配置与 `AudioInferencePipeline.start()` 的 `ZipformerConfig` 完全一致（引擎对已初始化实例直接返回，配置不一致会被静默忽略）
- PortAudio 回退路径行为不变

**Ask First:**
- 改动录音循环线程模型（迁 isolate）——本次不做
- 重新打包 deb / 安装到系统（需 sudo）

**Never:**
- 不改 Fcitx5 插件；不动 `HotkeyController` 状态机语义
- 不清理遗留 `modelPath` 的下载/向导逻辑（另行处理）

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| 正常识别 | 预热完成，按键→说话 | 中间结果亚秒级持续刷新 | N/A |
| 短语句快停 | 说 1–2 秒立即按停 | 完整文本本次提交，不遗留到下次 | N/A |
| 冷启动/切换后首按 | 刚启动或刚切换模型/引擎 | 预热已完成，首按无模型加载延迟 | 预热失败仅 WARN 不阻塞 |
| 模型目录缺失 | `models/zipformer/` 不存在 | WARN `modelNotFound`，下载向导流程不变 | 静默降级 |
| libpulse 不可用 | 无 PulseAudio 环境 | 回退 PortAudio，与现状一致 | 既有逻辑 |

</frozen-after-approval>

## Code Map

- `voice_capsule/lib/ffi/libpulse_simple_ffi.dart` -- 缺 `pa_buffer_attr` 结构体，`pa_simple_new` 第 8 参只能传 nullptr
- `voice_capsule/lib/services/pulse_audio_capture.dart:89-99` -- `simpleNew` 调用点，97 行 nullptr 即根因 1
- `voice_capsule/lib/main.dart:157-208` -- `_preInitializeEngine`（161-165 行遗留路径，根因 2）+ `_warmupEngineWithSilence`
- `voice_capsule/lib/main.dart:499-525` -- `onModelSwitch`/`onEngineSwitch` 回调，切换后未重新预热
- `voice_capsule/lib/services/audio_inference_pipeline.dart:321-347` -- 管线侧配置构造（正确路径 `getModelPathForEngine`），预初始化须与之对齐
- `voice_capsule/lib/services/asr/asr_engine_factory.dart` -- 已有 `createConfig`，可扩展为两处共用

## Tasks & Acceptance

**Execution:**
- [x] `voice_capsule/lib/ffi/libpulse_simple_ffi.dart` -- 新增 `PaBufferAttr` 结构体（maxlength/tlength/prebuf/minreq/fragsize，Uint32），`simpleNew` 对应参数改为 `Pointer<PaBufferAttr>` -- 使缓冲属性可配置
- [x] `voice_capsule/lib/services/pulse_audio_capture.dart` -- `initialize()` 分配并传入 attr：`fragsize=6400`，其余字段 0xFFFFFFFF(-1)；`_cleanup` 释放 -- 恢复 ~100ms 实时投递
- [x] `voice_capsule/lib/main.dart` -- `_preInitializeEngine` zipformer 分支改用 `getModelPathForEngine(EngineType.zipformer)`，配置与管线共用同一构造（杜绝漂移）；修正 `_asrEngine == null` 时 `_asrEngine!` 空解引用 -- 让预热真正生效
- [x] `voice_capsule/lib/main.dart` -- `onModelSwitch`/`onEngineSwitch` 回调末尾重新预初始化+预热 -- 切换后首按不付加载代价
- [x] `voice_capsule/test/services/` -- 补测试：buffer_attr 传递值正确；预初始化用 `getModelPathForEngine` -- 防回归

**Acceptance Criteria:**
- Given 应用启动且 `models/zipformer/` 存在，when 查看诊断日志，then 出现 `✅ ASR 引擎预初始化完成` 与 `✅ 引擎推理预热完成`，无 `modelNotFound`
- Given 预热完成，when 按键立即说话，then 识别结果亚秒级刷新；说完立即按停也完整提交本句
- Given 切换模型/引擎后，when 首次按键，then 无 >1s 初始化延迟
- Given `flutter test`，then 无新增失败（既有 settings_service_test 1 例为已知遗留）

## Spec Change Log

- 2026-07-09 用户真机验证反馈（大幅改善但句尾丢字、实时显示消失）触发追加修复：
  ① pa_simple_read 全程阻塞主 isolate 饿死事件循环（旧 PortAudio 的等待在定时器休眠、UI 自由）——经用户批准改为 `Isolate.run` 后台读取（解除上轮 Ask First 门禁）；
  ② `pipeline.stop()` 不排空服务端滞留尾音（~300ms 含最后几个字）——inputFinished 前追加 3 碎片排空，VAD 停止路径除外。
  KEEP：fragsize=100ms 缓冲属性与共用配置构造保持不变。
- 2026-07-09 二次验证反馈"什么都不显示"触发根因再定位（虚拟麦克风+受控 GUI 实例复现）：
  **总根因＝PipeWire 上 `pa_simple_flush` 对录音流是 no-op**（返回成功但服务端队列原封不动）。
  录音流"warmup 后常开"设计下，空闲期积压持续增长，录音按 1x 速率只能读到"积压时长之前"的旧数据：
  定量实证——应用静置 20 秒后录音，前 199 块（19.9s）全为陈旧静音，第 200 块起才出现真实语音。
  这一并解释了 0.2.6 以来全部症状（迟滞、需反复按键、上一句下次才出现、句尾丢字、无实时显示）。
  修复：废弃 flush 方案，改为 **start() 重建全新录音流、stop() 释放流**（实测重建仅 4-12ms）；
  `PulseAudioCapture.start()` 变为 async（等待在飞后台读取后再释放旧流），facade 调用点加 await。
  前两轮的 fragsize/预热/后台读取/尾音排空修复仍然有效且保留。

## Design Notes

- PulseAudio 录音流按 fragsize 投递；不设置时默认值大，`pa_simple_read` 阻塞到碎片凑齐——即"说了几秒才蹦出结果"的机制。6400 bytes 恰为一次 `read()` 的量，与循环节拍对齐，阻塞恢复到旧 PortAudio 路径同量级。`pa_simple_new` 带 attr 时内部自动 `PA_STREAM_ADJUST_LATENCY`。
- 配置一致性是硬约束：`ZipformerEngine.initialize()` 首行 `if (_isInitialized) return none`，预热用错配置＝运行期用错配置。

## Verification

**Commands:**
- `cd voice_capsule && flutter analyze lib test` -- expected: 无新增告警
- `cd voice_capsule && flutter test` -- expected: 除既有遗留失败外全绿
- `cd voice_capsule && flutter build linux --debug` -- expected: 编译通过

**Manual checks (if no CLI):**
- 隔离 `XDG_RUNTIME_DIR` 本机运行：日志确认预热两条 ✅；按键说话，胶囊亚秒级出字；说完立即按停文本完整上屏；连续 5 轮无"上一句下次才出现"
- 修复合入后需用 build-pkg 重新打包安装才生效（当前系统的 "0.2.9" deb 为 7月9日 02:36 旧构建，不含 Portal 代码，版本号注入有误）

## Suggested Review Order

**根因 1：录音流缓冲属性（fragsize）**

- 修复入口：显式 fragsize 取代 nullptr，服务端按 100ms 投递
  [`pulse_audio_capture.dart:87`](../../voice_capsule/lib/services/pulse_audio_capture.dart#L87)

- fragsize 与 read() 量同源的具名常量（审查后加固，测试锁定）
  [`pulse_audio_capture.dart:13`](../../voice_capsule/lib/services/pulse_audio_capture.dart#L13)

- attr 实际传入 pa_simple_new 的调用点
  [`pulse_audio_capture.dart:112`](../../voice_capsule/lib/services/pulse_audio_capture.dart#L112)

- 新增 PaBufferAttr FFI 结构体（5×Uint32，与 C 布局一致）
  [`libpulse_simple_ffi.dart:28`](../../voice_capsule/lib/ffi/libpulse_simple_ffi.dart#L28)

**根因 2：预初始化路径与配置单一来源**

- 共用配置构造：正确模型路径 + 管线同参（消除漂移的核心设计）
  [`audio_inference_pipeline.dart:280`](../../voice_capsule/lib/services/audio_inference_pipeline.dart#L280)

- 预初始化改用共用构造，并修复原 null 解引用
  [`main.dart:157`](../../voice_capsule/lib/main.dart#L157)

- warmup 改收局部 engine 参数，消除 await 期引擎被切换的 TOCTOU
  [`main.dart:185`](../../voice_capsule/lib/main.dart#L185)

- 管线 start() 改为调用共用构造
  [`audio_inference_pipeline.dart:361`](../../voice_capsule/lib/services/audio_inference_pipeline.dart#L361)

**切换后重新预热**

- switchEngine 后立即预热新引擎（首按不付加载代价）
  [`main.dart:531`](../../voice_capsule/lib/main.dart#L531)

- switchModelType 处为防御性调用（运行期不换模型，注释已澄清）
  [`main.dart:500`](../../voice_capsule/lib/main.dart#L500)

**外围：防回归测试**

- 配置构造测试：modelDir 必须来自 getModelPathForEngine（直击根因 2）
  [`audio_inference_pipeline_config_test.dart:1`](../../voice_capsule/test/services/audio_inference_pipeline_config_test.dart#L1)

- PaBufferAttr 布局与 fragsizeBytes 同源断言
  [`pulse_audio_capture_test.dart:1`](../../voice_capsule/test/services/pulse_audio_capture_test.dart#L1)
