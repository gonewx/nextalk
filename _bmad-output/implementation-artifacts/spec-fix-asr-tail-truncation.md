---
title: 修复 ASR 尾字截断并串入下一次转录
type: bug-fix
status: done
created: 2026-08-02
owner: Decker
route: plan-code-review
baseline_commit: e9b464f8f71c5be604829d529339c35e168f175c
---

# 修复 ASR 尾字截断并串入下一次转录

## 问题陈述

每次语音输入的最后 2-3 个字不上屏，且会出现在下一次转录的开头。

## 根因（真机实测已证实）

流式 transducer 的 `IsReady()` 判定只有一行：

```cpp
return s->GetNumProcessedFrames() + model_->ChunkSize() < s->NumFramesReady();
```

**不检查 `input_finished_`**。因此松开快捷键时，音频末尾不足一个 chunk（T_≈32 帧 / 约 320ms）的尾帧永远进不了解码循环——`while (isReady()) decode()` 直接返回 false。随后 `reset()` 只做 `start_frame_index_ += num_processed_frames_`，源码注释明写 `// we don't reset the feature extractor`，未消费的尾帧原样留在特征提取器里，下一次录音时被当作开头解码出来。

**实测证据**（真实模型 + `test_wavs/0.wav`，截掉末尾 258ms 静音以模拟"话音正说着就松键"）：

| 步骤 | 输出 |
|---|---|
| 急停后跑干 decode | `昨天是 MONDAY TODAY IS LIBR THE DAY AFTER TOMORROW是星` |
| 再补 0.6s 静音后 | `昨天是 MONDAY TODAY IS LIBR THE DAY AFTER TOMORROW是星期三` |

"期三"两字**仅靠 padding 才解出**，丢字量级与用户描述一致。

同时**否证**两条先前假设：

1. `inputFinished()` 对 transducer 是**空操作**——调用后跑干 decode 没有多解出任何内容。
2. `inputFinished()` 后 `reset()` 再喂音频**不会崩溃**（曾有 KNF_LOG(FATAL) 之说，实测不成立，与线上不崩的现象一致）。

**结论**：padding 是唯一真正解决丢字的手段；重建 stream 只保证会话隔离（残留是丢字的下游后果，padding 补上后串话自然消失）。

## 关键约束

- **SenseVoice 的 `inputFinished()` 必须保留**：其实现是 `voiceActivityDetectorFlush()` + `_processVadSegments()`，是离线引擎出结果的必要步骤。修改**不得**在 pipeline 层无条件删除该调用，必须按引擎语义分派。
- `initialize()` 在 `_isInitialized` 为真时早退（`zipformer_engine.dart:87-89`），OnlineStream 全生命周期只建一次——这是残留能跨会话累积的前提。
- 涉及 3 个 `inputFinished()` 调用点，其中 `_handleDeviceLost()` 与 PTT 累积模式路径语义各不相同，须分别处理。

## 方案

在 `ASREngine` 接口新增 `finalizeUtterance()`，把"一次发话如何收尾"的知识收进各引擎自己：

- **Zipformer**：喂 0.6s 静音 padding → 跑干 decode → 取结果 → 销毁并重建 OnlineStream（隔离会话，替代不可靠的 `reset()`）。
- **SenseVoice**：沿用现有 `inputFinished()` 语义（flush VAD + 处理尾段）。

Pipeline 层三处收尾统一改调 `finalizeUtterance()`，不再直接调 `inputFinished()`。

## 任务

按依赖顺序执行。

- [x] **任务 1：`lib/services/asr/asr_engine.dart`** — 在 `ASREngine` 抽象类新增 `ASRResult finalizeUtterance();`，文档注明：调用方在一次发话结束时调用且只调用一次，实现须保证返回的是包含尾帧的最终结果，并令引擎可安全接受下一次发话。保留 `inputFinished()` 声明并标注 `@Deprecated`，说明对流式 transducer 无效。

- [x] **任务 2：`lib/services/asr/zipformer_engine.dart`** — 实现 `finalizeUtterance()`：
   - 新增私有常量 `_tailPaddingSeconds = 0.6`（注释说明 0.3s=30 帧 < 32 帧窗口余量不足）。
   - `calloc<Float>` 分配 `16000 * 0.6` 个零样本 → `acceptWaveform` → `while (isReady()) decode()` → `getResult()`，**`finally` 中 `calloc.free`**。
   - 取到结果后调用新增私有方法 `_recreateStream()`：`destroyOnlineStream(_stream!)` → `createOnlineStream(_recognizer!)`，失败时置 `_lastError = ASRError.streamCreateFailed` 并保留旧指针为 null 以免野指针。
   - 未初始化时返回 `ASRResult.empty()`。

- [x] **任务 3：`lib/services/asr/sensevoice_engine.dart`** — 实现 `finalizeUtterance()`：调用现有 `inputFinished()` 逻辑（flush VAD + `_processVadSegments()`）后返回 `getResult()`，保持既有行为不变。

- [x] **任务 4：`test/audio_inference_pipeline_test.dart:75`** — `MockASREngine` 实现 `finalizeUtterance()`：记录调用次数，返回预设文本，供任务 9 的断言使用。（`SherpaService` 不实现 `ASREngine`，其 `inputFinished()` 属独立 API，本次不改。）

- [x] **任务 5：`lib/services/audio_inference_pipeline.dart:442-466`**（`stop()` 主收尾路径）— 删除 `inputFinished()` 调用与其后的 decode 循环及 `reset()`，改为单次 `final result = _asrEngine.finalizeUtterance();` 并用其文本走原有上屏逻辑。

- [x] **任务 6：`lib/services/audio_inference_pipeline.dart:713-755`**（`_handleEndpoint()` VAD 路径）— 非 PTT 累积模式分支改调 `finalizeUtterance()` 并移除紧随的 `reset()`；**PTT 累积模式分支保持不调用**（现有注释说明累积语义，不得改动）。

- [x] **任务 7：`lib/services/audio_inference_pipeline.dart:665-687`**（`_handleDeviceLost()`）— 改调 `finalizeUtterance()` 取 `preservedText`，保留现有 `try/catch` 兜底。

- [x] **任务 8：`lib/services/audio_inference_pipeline.dart:565-573`**（VAD 自动停止清理）— 移除此处 `_asrEngine.reset()`（会话隔离已由 `finalizeUtterance()` 内的重建承担），其余状态清理保持不变。

- [x] **任务 9：`test/audio_inference_pipeline_*_test.dart`** — 更新 fake ASR 引擎实现 `finalizeUtterance()`；新增测试：(a) `stop()` 只调用 `finalizeUtterance()` 一次且不再调 `inputFinished()`/`reset()`；(b) PTT 累积模式下不调用 `finalizeUtterance()`；(c) 设备丢失路径仍能取到保留文本。

## 验收标准

**AC1 尾字完整上屏**
- Given 用户说完一句话后立即松开快捷键（话音末尾无自然静音）
- When 引擎收尾
- Then 完整文本（含最后 2-3 个字）上屏，不再截断

**AC2 无跨会话串话**
- Given 上一次录音已结束并上屏
- When 用户开始新一次录音
- Then 新一次转录结果不含上一次的任何尾部内容

**AC3 SenseVoice 路径不回归**
- Given 引擎配置为 SenseVoice
- When 一次发话结束
- Then VAD flush 与尾段处理照旧执行，识别结果与修改前一致

**AC4 PTT 累积模式不回归**
- Given PTT 累积模式下 VAD 检测到端点
- When `_handleEndpoint()` 执行
- Then 不执行发话收尾，后续音频仍能继续累积到同一次转录

**AC5 设备丢失仍保留文本**
- Given 录音中音频设备丢失
- When `_handleDeviceLost()` 触发
- Then 已识别文本被保留并随 `isDeviceLost=true` 事件发出

**AC6 无内存泄漏**
- Given 连续 20 次录音—上屏循环
- When 每次都走 `finalizeUtterance()`
- Then padding 缓冲区全部释放、旧 OnlineStream 全部销毁，无指针泄漏或崩溃

## 验证命令

```bash
cd voice_capsule && flutter analyze
cd voice_capsule && flutter test
```

基线：修改前 pipeline 相关测试 58 项全绿，回归后须仍全绿。

真机验证 AC1/AC2：`flutter run -d linux`，连续两次短语音（每次话音末尾立即松键），确认尾字完整且第二次开头干净。

## 待验假设

- `_tailPaddingSeconds = 0.6` 取值依据是 T_=32 帧窗口的余量推算，实测 0.6s 有效；0.3s 未单独验证是否足够。若真机感到收尾延迟偏高，可下调至 0.4s 重测 AC1。
- `ChunkSize()`/`ChunkShift()` 的 32/16 取值来自上游文档描述的 typical value，未在本机打印确认；不影响修法正确性。

## Suggested Review Order

**核心修法：尾帧解码 + 会话隔离**

- 补静音 padding 把尾音顶过 chunk 边界，解码后取其掉 `reset()` 改用重建流
  [`zipformer_engine.dart:358`](../../voice_capsule/lib/services/asr/zipformer_engine.dart#L358)
- 流重建分离为独立私有方法，失败时标记 `_needsStreamRecovery` 而非静默失效
  [`zipformer_engine.dart:389`](../../voice_capsule/lib/services/asr/zipformer_engine.dart#L389)

**自愈机制：流重建失败不丢引擎**

- `ensureStreamReady()` 接口声明：每次发话前校验，失败可重试一次
  [`asr_engine.dart:285`](../../voice_capsule/lib/services/asr/asr_engine.dart#L285)
- `ensureStreamReady()` 实现：重试流创建，成功清除恢复标记
  [`zipformer_engine.dart:411`](../../voice_capsule/lib/services/asr/zipformer_engine.dart#L411)
- pipeline `start()` 中调用，将静默失效转为 explicit `recognizerFailed`
  [`audio_inference_pipeline.dart:375`](../../voice_capsule/lib/services/audio_inference_pipeline.dart#L375)

**Pipeline 三处收尾统一改造**

- `stop()` 主收尾：VAD 已收尾时跳过 `finalizeUtterance()` 防止重复 padding
  [`audio_inference_pipeline.dart:449`](../../voice_capsule/lib/services/audio_inference_pipeline.dart#L449)
- VAD 端点处理：PTT 累积模式只读结果不收尾，其余走 `finalizeUtterance()`
  [`audio_inference_pipeline.dart:720`](../../voice_capsule/lib/services/audio_inference_pipeline.dart#L720)
- 设备丢失：同样走 `finalizeUtterance()` 保住尾字
  [`audio_inference_pipeline.dart:686`](../../voice_capsule/lib/services/audio_inference_pipeline.dart#L686)
- 移除 `inputFinished()` + `reset()` 调用链：这三个地方的改动都删掉了这个无效收尾
  [`audio_inference_pipeline.dart:454`](../../voice_capsule/lib/services/audio_inference_pipeline.dart#L454)

**SenseVoice：保留现有语义不回归**

- 离线引擎的 `finalizeUtterance()` 只是 flush VAD + 取结果，不引入流重建
  [`sensevoice_engine.dart:838`](../../voice_capsule/lib/services/asr/sensevoice_engine.dart#L838)

**测试：收尾契约验证**

- 4 条新增回归测试覆盖 stop/VAD/设备丢失/PTT 累积四路收尾
  [`audio_inference_pipeline_test.dart:1320`](../../voice_capsule/test/audio_inference_pipeline_test.dart#L1320)
