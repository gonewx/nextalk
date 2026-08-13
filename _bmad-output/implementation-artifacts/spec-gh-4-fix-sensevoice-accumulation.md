---
title: '修复 SenseVoice 累积文本跨会话残留 (issue #4)'
type: 'bugfix'
created: '2026-08-13'
status: 'done'
baseline_commit: '3569d29bc42ca7933932fd3fe507fb56ea58728a'
review_loop_iteration: 0
context: []
---

## Intent

**Problem:** GitHub issue #4：SenseVoice 引擎下每次语音输入会把之前所有会话的识别文本拼接到新输入前。根因已验证：`SenseVoiceEngine.finalizeUtterance()` 只 flush VAD + 返回 `_lastResult`，不清空 `_accumulatedText`/`_lastResult`；而 pipeline 自 38e9e9c 起不再调用 `_asrEngine.reset()`，会话隔离完全依赖 `finalizeUtterance()`。这违反了 ASREngine 接口契约「必须使引擎与上一次发话隔离，不得把残留内容带入下一次发话」(asr_engine.dart:276-277)。

**Approach:** 在 `SenseVoiceEngine.finalizeUtterance()` 返回结果后清空本会话累积状态（`_lastResult`、`_accumulatedText`、`_hasEndpoint`），与 `reset()` 的清理语义对齐；并在 pipeline 测试层新增「SenseVoice 式累积引擎」契约测试，固化两次发话文本隔离的行为，防止回归。

## Boundaries & Constraints

**Always:**
- `finalizeUtterance()` 必须返回含尾帧的完整结果（先 flush 后取结果再清理，顺序不可颠倒）
- 清理后引擎状态须与 `reset()` 后的状态一致，保证「返回后引擎可安全接收下一次发话」
- 会话内跨停顿累积（PTT 连续说话）不得受影响：VAD 端点路径 `_handleEndpoint()` 的 PTT 分支只 `getResult()` 不调 `finalizeUtterance()`，无需改动
- 回归测试沿用 38e9e9c 的 pipeline mock 引擎测试模式，不引入 FFI mock 设施

**Ask First:**
- 是否需要同步清理已废弃的 `inputFinished()`（无调用点，默认不动）

**Never:**
- 不改 `AudioInferencePipeline`（收尾契约正确，问题只在 SenseVoice 引擎侧）
- 不改 Zipformer 引擎
- 不引入 mock FFI / 重构 SenseVoiceEngine 依赖注入（超出 bugfix 范围）

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| HAPPY_PATH | 两次 PTT 录音「今天天气不错」→「我们明天打羽毛球」 | 第二次上屏仅「我们明天打羽毛球」，不含历史文本 | N/A |
| PTT 会话内停顿 | 一次按键内「今天天气不错」停顿「我们明天打羽毛球」 | 上屏累积文本，跨停顿累积保留 | N/A |
| VAD 自动停止模式 | `autoStopOnEndpoint: true` 下连续两次发话 | 每次发话独立，无历史拼接 | N/A |
| 设备丢失 | 录音中设备断开 | 保留下文文本（finalizeUtterance 已取结果），下次录音干净 | 取文本失败时保留 `_lastEmittedText`（现有逻辑） |

## Code Map

- `voice_capsule/lib/services/asr/sensevoice_engine.dart` -- 修复目标。`finalizeUtterance()` (L837-843) 只 flush+返回不清状态；`reset()` (L811-821) 的清理逻辑即清理模板；`_processVadSegments()` (L624-659) 中 L637-641 是累积 append 点
- `voice_capsule/lib/services/asr/asr_engine.dart` -- 接口契约 (L273-283)：finalizeUtterance 必须隔离会话、不得带残留入下一次发话（违规即 bug 本体）
- `voice_capsule/lib/services/audio_inference_pipeline.dart` -- 只读约束。`stop()` (L455-457) 非 VAD 触发时调 `finalizeUtterance()` 一次；L476-477 注释确认不再调 reset()；`_handleEndpoint()` (L731-733) PTT 分支只 getResult 不收尾（会话内累积依赖此行为，不可改）
- `voice_capsule/test/audio_inference_pipeline_test.dart` -- 回归测试落点。MockASREngine (L96-111) 已有 finalizeUtteranceCalls 跟踪；L1324+「尾字截断修复」group 是既有契约测试的放置处

## Tasks & Acceptance

**Execution:**
- [x] `voice_capsule/lib/services/asr/sensevoice_engine.dart` -- 在 `finalizeUtterance()` 中取结果后清空 `_lastResult`/`_accumulatedText`/`_hasEndpoint` -- 补齐接口契约的会话隔离要求，修复跨会话文本拼接
- [x] `voice_capsule/test/audio_inference_pipeline_test.dart` -- 增强 MockASREngine 支持 SenseVoice 式累积语义（getResult 返回累积文本、finalizeUtterance 返回并清空累积），新增测试：两次 stop() 循环第二次结果不含第一次文本 -- 固化会话隔离契约，防回归（SenseVoiceEngine 依赖真实 FFI+模型无法直接单测，pipeline mock 是项目既有模式）
- [x] `voice_capsule/lib/services/asr/sensevoice_engine.dart` -- 更新 `finalizeUtterance()` 与 `inputFinished()` 的注释，明确「收尾后清空累积缓冲」语义 -- 防止未来实现者误删清理逻辑

**Acceptance Criteria:**
- Given SenseVoice 引擎已完成一次发话（finalizeUtterance 被调用），when 再次开始新发话，then 新发话的识别结果不含上次发话的任何文本
- Given PTT 模式一次按键内跨停顿说话，when VAD 端点触发（PTT 分支），then 累积文本保留、不收尾
- Given 新回归测试，when 引擎实现违反「finalizeUtterance 后清空累积」契约，then 测试失败

## Spec Change Log

## Design Notes

清理语义与 `reset()` 完全对齐（L818-820），保证任意调用时序下引擎状态一致。顺序关键：`_flushVadAndProcess()` → `getResult()` 取含尾帧结果 → 清空。若先清空再 flush，flush 出的尾段会被 append 到已清空的缓冲，结果丢失尾字（与 38e9e9c 的修复目标相悖）。

## Verification

**Commands:**
- `cd voice_capsule && flutter test test/audio_inference_pipeline_test.dart` -- expected: 全绿（含新增会话隔离测试）
- `cd voice_capsule && flutter test` -- expected: 全量测试通过（707+ 项基线）
- `cd voice_capsule && flutter analyze` -- expected: 无新增 warning

## Suggested Review Order

**会话隔离核心修复**

- 入口：finalizeUtterance 取结果后 finally 清理 + 原生 VAD reset，会话隔离的唯一保障
  [`sensevoice_engine.dart:856`](../../voice_capsule/lib/services/asr/sensevoice_engine.dart#L856)

- _clearSessionState 抽取，reset/dispose/finalize 三处收敛防漏清
  [`sensevoice_engine.dart:811`](../../voice_capsule/lib/services/asr/sensevoice_engine.dart#L811)

- reset() 复用同一清理，语义对齐的参照实现
  [`sensevoice_engine.dart:825`](../../voice_capsule/lib/services/asr/sensevoice_engine.dart#L825)

**回归测试契约**

- issue #4 会话隔离测试：两次发话文本隔离 + finalizeUtteranceCalls==2 锚定收尾契约
  [`audio_inference_pipeline_test.dart:1471`](../../voice_capsule/test/audio_inference_pipeline_test.dart#L1471)

- mock 累积语义模拟 VAD 段累积与 flush 收尾，保真度提升（含顺序契约限制说明）
  [`audio_inference_pipeline_test.dart:114`](../../voice_capsule/test/audio_inference_pipeline_test.dart#L114)
