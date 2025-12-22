# Story 2.6: VAD 端点检测 (VAD Endpoint Detection)

Status: done

## Prerequisites

> **前置条件**: Story 2-1 ~ 2-5 必须完成
> - ✅ Flutter Linux 构建系统已配置 (Story 2-1)
> - ✅ PortAudio FFI 绑定已完成，AudioCapture 已实现 (Story 2-2)
> - ✅ Sherpa-onnx FFI 绑定已完成，SherpaService 已实现 (Story 2-3)
> - ✅ ModelManager 已实现 (Story 2-4)
> - ✅ AudioInferencePipeline 已实现，`isEndpoint()` 接口已就绪 (Story 2-5)
> - ⚠️ 本 Story 完成后，用户可实现"即说即打"体验

## Story

As a **用户**,
I want **停止说话后系统自动完成输入**,
So that **无需手动确认，实现"即说即打"体验**。

## Acceptance Criteria

| AC | 描述 | 验证方法 |
|----|------|----------|
| AC1 | 自动端点触发: 检测到持续静音超过阈值（默认 1.5s）时，VAD 触发端点事件 | 说话后保持静音，观察 `endpointStream` 发出事件 |
| AC2 | 自动停止录音: 端点触发后自动停止录音并返回最终识别文本 | 订阅 `endpointStream`，验证收到 `EndpointEvent`，`autoStop` 为 true 时流水线自动停止 |
| AC3 | 自定义静音阈值: 可配置静音阈值参数 | 设置不同的 `silenceThreshold` 值，验证端点触发时间变化 |
| AC4 | 短暂停顿不触发: 说话中间有短暂停顿（< 阈值）时，不触发端点，继续录音 | 说话时短暂停顿，验证录音继续 |
| AC5 | 端点事件流: 通过 `endpointStream` 通知端点触发，包含最终文本和统计信息 | 订阅 `endpointStream` 验证事件格式 |
| AC6 | 自动停止模式: 支持 `autoStopOnEndpoint` 选项，启用时自动停止，禁用时仅发送事件 | 分别测试两种模式行为 |
| AC7 | 重置后继续: 端点触发后重置流状态，支持立即开始新一轮识别 | 端点触发后立即再次说话，验证新识别正常工作 |
| AC8 | 与手动停止兼容: VAD 自动停止与手动调用 `stop()` 互不冲突，不产生重复事件 | 在 VAD 触发前手动 stop()，验证无异常且只收到一个事件 |

## 开始前确认

```bash
# 执行以下检查，全部通过后方可开始
[ ] flutter test test/audio_inference_pipeline_test.dart  # Pipeline 测试通过
[ ] flutter test test/sherpa_service_test.dart           # SherpaService 测试通过
[ ] ls -la ~/.local/share/nextalk/models/*/              # 模型文件存在
```

## 技术规格

### 核心架构图 [Source: docs/architecture.md#4.2, Story 2-5]

```text
┌─────────────────────────────────────────────────────────────────────────┐
│                    AudioInferencePipeline (增强版)                       │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────┐    ┌───────────────┐    ┌──────────────────────────┐  │
│  │ AudioCapture │    │ SharedBuffer  │    │   SherpaService          │  │
│  │              │───▶│ Pointer<Float>│───▶│                          │  │
│  │ Pa_ReadStream│    │  (零拷贝)     │    │ acceptWaveform()         │  │
│  └──────────────┘    └───────────────┘    │ decode()                 │  │
│                                           │ getResult()              │  │
│                                           │ isEndpoint() ◀─── VAD    │  │
│                                           │ reset()                  │  │
│                                           └──────────────────────────┘  │
│                                                      │                   │
│                       ┌──────────────────────────────┼───────────────┐  │
│                       │                              │               │  │
│                       ▼                              ▼               ▼  │
│          ┌──────────────────────┐    ┌────────────────────┐    ┌─────┐ │
│          │ StreamController     │    │ VAD EndpointDetector│    │Auto │ │
│          │   resultStream       │──▶ │   endpointStream    │──▶ │Stop │ │
│          │   stateStream        │    │                      │    │Logic│ │
│          └──────────────────────┘    └────────────────────┘    └─────┘ │
└─────────────────────────────────────────────────────────────────────────┘
```

### VAD 端点检测规则 [Source: voice_capsule/lib/services/sherpa_service.dart]

Sherpa-onnx 内置三条端点检测规则，已在 `SherpaConfig` 中配置：

| 规则 | 参数 | 默认值 | 说明 |
|------|------|--------|------|
| Rule 1 | `rule1MinTrailingSilence` | 2.4s | 解码前的最小尾部静音（长停顿） |
| Rule 2 | `rule2MinTrailingSilence` | 1.2s | 解码后的最小尾部静音（标准停顿） |
| Rule 3 | `rule3MinUtteranceLength` | 20.0s | 最小语句长度（超长语音强制切分） |

**PRD 要求 (FR3)**: 默认停顿 ~1.5s 触发，与 `rule2MinTrailingSilence: 1.2` 接近。

### 新增类型定义

```dart
/// VAD 端点事件
class EndpointEvent {
  /// 最终识别文本
  final String finalText;

  /// 是否由 VAD 自动触发 (true: VAD, false: 手动 stop)
  final bool isVadTriggered;

  /// 端点触发前的识别时长 (毫秒)
  final int durationMs;

  /// 延迟统计
  final LatencyStats latencyStats;

  const EndpointEvent({
    required this.finalText,
    required this.isVadTriggered,
    required this.durationMs,
    required this.latencyStats,
  });
}

/// VAD 配置
class VadConfig {
  /// 是否启用 VAD 自动停止
  final bool autoStopOnEndpoint;

  /// 端点触发后是否自动重置流状态 (用于连续识别)
  final bool autoReset;

  /// 自定义 Rule 2 静音阈值 (秒)，null 表示使用 SherpaConfig 默认值
  /// ⚠️ 注意: 此值在 start() 时传递给 Sherpa，运行时修改需重启 Pipeline
  final double? silenceThresholdSec;

  const VadConfig({
    this.autoStopOnEndpoint = true,
    this.autoReset = false,
    this.silenceThresholdSec,
  });

  /// 默认配置: 自动停止，不自动重置
  factory VadConfig.defaultConfig() => const VadConfig();

  /// 连续识别配置: 不停止，自动重置
  factory VadConfig.continuous() => const VadConfig(
        autoStopOnEndpoint: false,
        autoReset: true,
      );
}
```

### 本 Story 使用的关键接口

| 接口 | 来源 | 说明 |
|------|------|------|
| `isEndpoint()` | SherpaService | 检查是否检测到端点 (核心 VAD 逻辑) |
| `reset()` | SherpaService | 重置流状态，清空缓冲区但保留模型 |
| `inputFinished()` | SherpaService | 标记输入结束，触发最终解码 |
| `latencyStats` | AudioInferencePipeline | 延迟统计 (Story 2-5 已实现) |

### 目标文件结构

```text
voice_capsule/lib/services/
├── audio_capture.dart            # ✅ 已存在 (Story 2-2)
├── sherpa_service.dart           # ✅ 已存在 (Story 2-3)
├── model_manager.dart            # ✅ 已存在 (Story 2-4)
└── audio_inference_pipeline.dart # 🔄 本 Story 修改 (新增 VAD 功能)
```

## Tasks / Subtasks

> **执行顺序**: Task 1 → Task 2 → Task 3 → Task 4 → Task 5

- [x] **Task 1: 新增 VAD 类型定义** (AC: #3, #5)
  - [x] 1.1 在 `audio_inference_pipeline.dart` 顶部新增 `EndpointEvent` 类 (参见技术规格)
  - [x] 1.2 新增 `VadConfig` 类 (参见技术规格)

- [x] **Task 2: 修改 AudioInferencePipeline 支持 VAD** (AC: #1, #2, #5, #6)
  - [x] 2.1 新增成员变量:
    - `_endpointController`: StreamController<EndpointEvent>.broadcast()
    - `_vadConfig`: VadConfig (默认配置)
    - `_recordingStartTime`: DateTime? (记录开始时间)
    - `_vadTriggeredStop`: bool (防止重复事件)
  - [x] 2.2 新增公开接口:
    - `endpointStream`: Stream<EndpointEvent>
    - `vadConfig`: VadConfig getter
  - [x] 2.3 修改构造函数，接受可选 `VadConfig? vadConfig` 参数
  - [x] 2.4 添加 `setVadConfig(VadConfig config)` 方法 (仅 idle 状态有效)
  - [x] 2.5 修改 `start()`:
    - 记录 `_recordingStartTime = DateTime.now()`
    - 重置 `_vadTriggeredStop = false`
    - 使用 `_vadConfig.silenceThresholdSec ?? 1.2` 初始化 SherpaConfig

- [x] **Task 3: 实现 VAD 端点检测逻辑** (AC: #1, #2, #4, #6, #7)
  - [x] 3.1 修改 `_processSingleChunk()`，在 `getResult()` 后检查端点:
    ```dart
    if (_sherpaService.isEndpoint()) {
      await _handleEndpoint();
    }
    ```
  - [x] 3.2 实现 `_handleEndpoint()` 方法:
    ```dart
    Future<void> _handleEndpoint() async {
      // 1. 调用 inputFinished() 确保最终解码
      _sherpaService.inputFinished();
      while (_sherpaService.isReady()) { _sherpaService.decode(); }
      final finalResult = _sherpaService.getResult();

      // 2. 计算录音时长
      final durationMs = _recordingStartTime != null
          ? DateTime.now().difference(_recordingStartTime!).inMilliseconds
          : 0;

      // 3. 创建并发送端点事件
      final event = EndpointEvent(
        finalText: finalResult.text,
        isVadTriggered: true,
        durationMs: durationMs,
        latencyStats: latencyStats,
      );
      if (!_isDisposed && !_endpointController.isClosed) {
        _endpointController.add(event);
      }

      // 4. 根据配置决定后续行为
      if (_vadConfig.autoStopOnEndpoint) {
        _vadTriggeredStop = true;  // 标记 VAD 触发，防止 stop() 重复发送事件
        _stopRequested = true;
      } else if (_vadConfig.autoReset) {
        _sherpaService.reset();
        _lastEmittedText = '';
        _recordingStartTime = DateTime.now();
      }
    }
    ```

- [x] **Task 4: 修改 stop() 和 dispose() 方法** (AC: #8)
  - [x] 4.1 修改 `stop()` 方法，检查 `_vadTriggeredStop` 防止重复事件:
    ```dart
    // 发送手动停止事件 (仅当不是 VAD 触发时)
    if (!_vadTriggeredStop && !_isDisposed && !_endpointController.isClosed) {
      final event = EndpointEvent(
        finalText: finalResult.text,
        isVadTriggered: false,
        durationMs: durationMs,
        latencyStats: latencyStats,
      );
      _endpointController.add(event);
    }
    // 重置标志
    _vadTriggeredStop = false;
    _recordingStartTime = null;
    ```
  - [x] 4.2 修改 `dispose()` 方法，关闭 `_endpointController`

- [x] **Task 5: 创建单元测试** (AC: #1-8)
  - [x] 5.1 创建/更新 `voice_capsule/test/audio_inference_pipeline_test.dart`
  - [x] 5.2 核心测试用例:
    - VAD 端点触发时 `endpointStream` 发出 `EndpointEvent`，`isVadTriggered` 为 true
    - 手动 `stop()` 时 `endpointStream` 发出事件，`isVadTriggered` 为 false
    - `autoStopOnEndpoint: true` 时端点触发后 `isRunning` 变为 false
    - `autoStopOnEndpoint: false` 时端点触发后 `isRunning` 保持 true
    - `autoReset: true` 时端点触发后流状态被重置
    - 自定义 `silenceThresholdSec` 正确传递给 `SherpaConfig`
    - `durationMs` 正确反映录音时长
    - `dispose()` 后 `endpointStream` 已关闭
  - [x] 5.3 边界条件测试:
    - **VAD + stop() 不产生重复事件**: VAD 触发后立即调用 stop()，验证只收到一个事件
    - **dispose() 期间发送事件**: 在 endpointStream 发送期间调用 dispose()，无异常
    - **连续端点检测**: isEndpoint() 连续返回 true 时只发送一个事件
  - [x] 5.4 Mock `isEndpoint()` 实现指导:
    ```dart
    class MockSherpaService extends SherpaService {
      int _endpointCallCount = 0;
      int triggerEndpointAfterCalls = 0; // >0 时，N 次调用后返回 true
      bool _endpointTriggered = false;

      @override
      bool isEndpoint() {
        if (_endpointTriggered) return false; // 已触发过，不再触发
        _endpointCallCount++;
        if (triggerEndpointAfterCalls > 0 &&
            _endpointCallCount >= triggerEndpointAfterCalls) {
          _endpointTriggered = true;
          return true;
        }
        return false;
      }

      void resetEndpointMock() {
        _endpointCallCount = 0;
        _endpointTriggered = false;
      }
    }
    ```
  - [x] 5.5 运行测试: `flutter test test/audio_inference_pipeline_test.dart`

## Dev Notes

### 架构约束与禁止事项

| 类别 | 约束 | 原因 |
|------|------|------|
| **FFI** | 禁止 `Isolate.run()` 做 VAD 检测 | FFI 指针不能跨 Isolate，会 crash |
| **VAD 调用时机** | `isEndpoint()` 必须在 `decode()` 后调用 | 否则结果不准确 |
| **reset() 语义** | `reset()` 只清空缓冲区，不释放模型 | 用于连续识别模式 |
| **reset() 调用时机** | `autoStopOnEndpoint: true` 时不调用 `reset()` | Pipeline 停止后无需重置 |
| **reset() 调用时机** | `autoReset: true` 时在端点后调用 `reset()` | 支持连续识别 |
| **重复事件防护** | 使用 `_vadTriggeredStop` 标志 | 防止 VAD 和 stop() 发送重复事件 |
| **inputFinished()** | VAD 触发时必须调用 | 确保获取完整最终结果 |
| **StreamController** | 发送前检查 `!_isDisposed && !_controller.isClosed` | 防止关闭后访问异常 |
| **autoReset 模式** | 重置时清空 `_lastEmittedText` | 避免去重逻辑失效 |
| **配置限制** | `silenceThresholdSec` 在 `start()` 时生效 | 运行时修改需重启 Pipeline |

### 与 Story 3-6 集成点

Story 3-6 (完整业务流串联) 需要使用本 Story 的 VAD 功能：

```dart
// Story 3-6 使用示例 (防重复处理)
bool _isSubmitting = false;
pipeline.endpointStream.listen((event) async {
  if (_isSubmitting) return; // 防止极端情况下的重复处理
  _isSubmitting = true;
  try {
    if (event.finalText.isNotEmpty) {
      await fcitxClient.sendText(event.finalText);
    }
    windowManager.hide();
  } finally {
    _isSubmitting = false;
  }
});
```

### 从 Story 2-5 继承的最佳实践

1. **Mock 类设计**: 使用 `triggerEndpointAfterCalls` 控制 `isEndpoint()` 返回时机
2. **StreamController 检查**: 发送事件前检查 `!_isDisposed && !_controller.isClosed`
3. **可中断延迟**: 使用 `_interruptibleDelay()` 而非固定 `Future.delayed`
4. **延迟统计**: `latencyStats` 已在 Story 2-5 实现，直接使用

### 快速验证脚本

```bash
#!/bin/bash
# scripts/verify-vad-story.sh
set -e
echo "=== Story 2-6 VAD 验证 ==="

cd voice_capsule

echo "1. 运行依赖服务测试..."
flutter test test/sherpa_service_test.dart --reporter compact
flutter test test/audio_inference_pipeline_test.dart --reporter compact

echo "2. 检查 VAD 相关类型..."
grep -q "class EndpointEvent" lib/services/audio_inference_pipeline.dart && echo "   ✅ EndpointEvent 存在"
grep -q "class VadConfig" lib/services/audio_inference_pipeline.dart && echo "   ✅ VadConfig 存在"
grep -q "endpointStream" lib/services/audio_inference_pipeline.dart && echo "   ✅ endpointStream 存在"
grep -q "_vadTriggeredStop" lib/services/audio_inference_pipeline.dart && echo "   ✅ 重复事件防护存在"

echo "=== 验证完成 ==="
```

### 外部资源

- [Sherpa-onnx Endpoint Detection](https://k2-fsa.github.io/sherpa/onnx/endpoint.html)
- [Sherpa-onnx C API: SherpaOnnxIsEndpoint](https://github.com/k2-fsa/sherpa-onnx/blob/master/sherpa-onnx/c-api/c-api.h)

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

无特殊调试记录

### Completion Notes List

- ✅ 实现 `EndpointEvent` 和 `VadConfig` 类型定义
- ✅ 新增 `_endpointController`、`_vadConfig`、`_recordingStartTime`、`_vadTriggeredStop` 成员变量
- ✅ 新增 `endpointStream`、`vadConfig` getter 和 `setVadConfig()` 方法
- ✅ 修改 `start()` 方法支持自定义静音阈值和 VAD 状态初始化
- ✅ 在 `_processSingleChunk()` 中添加 VAD 端点检测逻辑
- ✅ 实现 `_handleEndpoint()` 方法处理端点事件
- ✅ 在 `_startCaptureLoop()` 中添加 VAD 自动停止清理逻辑
- ✅ 修改 `stop()` 方法防止重复事件
- ✅ 修改 `dispose()` 方法关闭 `_endpointController`
- ✅ 新增 21 个 VAD 相关测试用例，全部通过 (50/50)

### Senior Developer Review (AI)

**审查时间:** 2025-12-22
**审查员:** Dev Agent (Amelia) - Code Review

**发现问题:** 3 High, 4 Medium, 3 Low

**已修复:**
- ✅ H1: 添加 AC4 "短暂停顿不触发" 直接测试验证 (2 个新测试)
- ✅ H2: Mock `reset()` 添加注释说明与真实 SherpaService 行为差异
- ✅ H3: `_handleEndpoint()` 添加 try-catch 异常处理
- ✅ M1: 提取默认静音阈值为常量 `kDefaultRule2Silence = 1.2`
- ✅ M2: Story File List 添加 sprint-status.yaml
- ✅ M4: `setVadConfig()` 添加调试日志

**未修复 (低优先级):**
- L1: `_recordingStartTime` 冗余 null 检查 (防御性代码，保留)
- L2: EndpointEvent/VadConfig 缺少 `==`/`hashCode` (当前不需要)
- L3: 测试组命名风格不统一 (风格问题，不影响功能)

**最终验证:** 52/52 测试通过

### Change Log

- 2025-12-22: Story created by SM Agent (Bob) - YOLO 模式
- 2025-12-22: Story validated by SM Agent (Bob) - 应用 4 个关键修复、3 个增强、4 个 LLM 优化
- 2025-12-22: Story implemented by Dev Agent (Amelia) - 全部 5 个 Task 完成，50 个测试通过
- 2025-12-22: Code review by Dev Agent (Amelia) - 修复 3 HIGH + 3 MEDIUM 问题，新增 2 个测试 (52/52)

### File List

**实际修改文件:**

| 文件 | 操作 | 说明 |
|------|------|------|
| `voice_capsule/lib/services/audio_inference_pipeline.dart` | 修改 | 新增 VAD 支持: EndpointEvent, VadConfig, endpointStream, _vadTriggeredStop, _handleEndpoint() |
| `voice_capsule/test/audio_inference_pipeline_test.dart` | 修改 | 新增 21 个 VAD 相关测试用例 (含边界条件)，扩展 MockSherpaService 支持端点检测 |
| `_bmad-output/implementation-artifacts/sprint-status.yaml` | 修改 | 更新 2-6-vad-endpoint-detection 状态 |

---
*References: docs/architecture.md#4.2, docs/prd.md#FR3, _bmad-output/epics.md#Story-2.6, Story 2-5*
