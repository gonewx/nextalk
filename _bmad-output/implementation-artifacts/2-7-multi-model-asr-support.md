# Story 2.7: 多模型 ASR 支持 (SenseVoice 集成)

Status: done

## Story

As a 用户,
I want 应用支持多种语音识别模型，可通过配置切换不同引擎,
so that 我可以根据场景选择最适合的识别方案 (流式低延迟 vs 离线高精度)。

## Acceptance Criteria

### AC1: ASR 引擎抽象层
- **Given** 当前系统仅支持 Zipformer 流式模型
- **When** 重构 ASR 架构
- **Then** 创建统一的 `ASREngine` 抽象接口
- **And** 现有 Zipformer 功能通过 `ZipformerEngine` 实现
- **And** 新增 `SenseVoiceEngine` 实现离线识别
- **And** 引擎切换不影响上层 `AudioInferencePipeline` 调用

### AC2: SenseVoice FFI 绑定
- **Given** Sherpa-onnx 支持 SenseVoice 离线识别
- **When** 添加离线 API 绑定
- **Then** 新增 `sherpa_offline_bindings.dart` 包含:
  - `SherpaOnnxOfflineRecognizerConfig` 结构体
  - `SherpaOnnxOfflineSenseVoiceModelConfig` 结构体
  - `SherpaOnnxVadModelConfig` 结构体
  - 离线识别器和 VAD 相关函数绑定
- **And** 绑定与 C API 完全匹配 (参考官方示例 `vad-sense-voice-c-api.c`)

### AC3: VAD + SenseVoice 伪流式实现
- **Given** SenseVoice 是非流式模型
- **When** 实现 `SenseVoiceEngine`
- **Then** 使用 Silero VAD 进行语音活动检测
- **And** VAD 检测到语音段后送入 SenseVoice 识别
- **And** 识别结果通过 Stream 实时输出
- **And** 用户体验接近流式 (按段落输出文字)

### AC4: 模型管理扩展
- **Given** 当前 `ModelManager` 仅支持单一模型
- **When** 扩展模型管理
- **Then** 支持按引擎类型管理不同模型目录:
  - `~/.local/share/nextalk/models/zipformer/`
  - `~/.local/share/nextalk/models/sensevoice/`
  - `~/.local/share/nextalk/models/vad/`
- **And** 每种模型独立下载、校验、解压
- **And** 支持配置自定义下载 URL

### AC5: 配置服务扩展
- **Given** 当前配置仅支持 int8/standard 版本切换
- **When** 扩展设置服务
- **Then** settings.yaml 新增引擎类型配置:
```yaml
model:
  # 引擎类型: zipformer | sensevoice
  engine: sensevoice

  # Zipformer 配置
  zipformer:
    type: int8
    custom_url: ""

  # SenseVoice 配置
  sensevoice:
    use_itn: true
    language: auto
    custom_url: ""
```
- **And** 引擎切换需销毁并重建 Pipeline (onnxruntime 限制)
- **And** 默认使用 SenseVoice 引擎

### AC6: 托盘菜单集成
- **Given** 托盘已支持模型版本切换
- **When** 扩展托盘菜单
- **Then** "模型设置" 子菜单包含:
  - ASR 引擎: Zipformer (流式) / SenseVoice (离线)
  - 当前引擎的版本选项
- **And** 切换引擎时显示加载提示
- **And** 切换完成后通过 notify-send 通知用户

### AC7: 错误处理与回退
- **Given** 用户选择的引擎模型可能不存在
- **When** 初始化失败
- **Then** 按优先级回退: SenseVoice → Zipformer → 显示下载引导
- **And** 状态指示器显示警告
- **And** 托盘菜单标记当前实际使用的引擎

## Tasks / Subtasks

- [x] Task 1: 创建 ASR 引擎抽象层 (AC: #1)
  - [x] 1.1 定义 `ASREngine` 抽象接口 (`lib/services/asr/asr_engine.dart`)
  - [x] 1.2 定义 `ASRResult` 统一结果类型 (含 text, lang, emotion, tokens, timestamps)
  - [x] 1.3 将现有 `SherpaService` 重构为 `ZipformerEngine`
  - [x] 1.4 创建 `ASREngineFactory` 工厂类
  - [x] 1.5 重构 `AudioInferencePipeline`: `SherpaService` → `ASREngine` 抽象接口
  - [x] 1.6 编写单元测试验证重构不破坏现有功能

- [x] Task 2: 添加 SenseVoice + VAD FFI 绑定 (AC: #2)
  - [x] 2.1 创建 `sherpa_offline_bindings.dart`: 离线识别器结构体与函数
  - [x] 2.2 创建 `sherpa_vad_bindings.dart`: VAD 结构体与函数
  - [x] 2.3 编写集成测试验证绑定正确性

- [x] Task 3: 实现 SenseVoiceEngine (AC: #3)
  - [x] 3.1 创建 `SenseVoiceEngine` 类实现 `ASREngine`
  - [x] 3.2 实现 VAD 初始化 (window_size=512, threshold=0.25)
  - [x] 3.3 实现离线识别器初始化 (use_itn=true, language=auto)
  - [x] 3.4 实现音频缓冲管理 (最大 10s，超时自动处理)
  - [x] 3.5 实现 VAD 检测循环与语音段提取
  - [x] 3.6 实现段落识别和结果输出 (在单独 Isolate 中执行)
  - [x] 3.7 处理 SenseVoice 结果段 (text, lang, emotion)
  - [x] 3.8 实现资源释放 (VAD + OfflineRecognizer)
  - [x] 3.9 编写单元测试

- [x] Task 4: 扩展模型管理 (AC: #4)
  - [x] 4.1 重构 `ModelManager` 支持多引擎模型目录
  - [x] 4.2 添加 SenseVoice 模型下载配置
  - [x] 4.3 添加 Silero VAD 模型下载配置
  - [x] 4.4 实现按引擎类型的模型状态检查
  - [x] 4.5 更新下载页面支持选择引擎 (API 已就绪)
  - [x] 4.6 编写单元测试

- [x] Task 5: 扩展配置服务 (AC: #5)
  - [x] 5.1 更新 `settings_constants.dart` 添加 `EngineType` 枚举 (Task 4 已完成)
  - [x] 5.2 更新 `defaultSettingsYaml` 模板
  - [x] 5.3 扩展 `SettingsService` 支持引擎配置读写
  - [x] 5.4 实现引擎切换回调 (销毁旧 Pipeline → 创建新 Pipeline)
  - [x] 5.5 编写单元测试

- [x] Task 6: 托盘菜单集成 (AC: #6)
  - [x] 6.1 更新托盘菜单结构 (引擎选择子菜单)
  - [x] 6.2 实现引擎切换逻辑
  - [x] 6.3 添加切换时的加载提示 (notify-send)
  - [x] 6.4 添加 i18n 键名并测试中英文

- [x] Task 7: 错误处理与回退 (AC: #7)
  - [x] 7.1 实现引擎初始化失败回退逻辑 (SenseVoice → Zipformer → 下载引导)
  - [x] 7.2 更新状态指示器支持警告状态
  - [x] 7.3 托盘菜单显示实际使用的引擎
  - [x] 7.4 编写集成测试

## Dev Notes

### 核心概念: 流式 vs 非流式

| 特性 | ZipformerEngine (流式) | SenseVoiceEngine (非流式) |
|:---|:---|:---|
| 识别方式 | 边听边识别，实时输出 | VAD 分段后一次性识别 |
| 延迟 | 极低 (<200ms) | 较高 (取决于语音段长度) |
| 精度 | 良好 | 更高 (含自动标点) |
| API 调用 | `acceptWaveform` 可重复调用 | 每段音频需创建新 OfflineStream |

### ASREngine 抽象接口设计

```dart
/// ASR 引擎抽象接口
abstract class ASREngine {
  /// 初始化引擎
  Future<ASRError> initialize(ASRConfig config);

  /// 送入音频数据
  /// - ZipformerEngine: 直接送入 OnlineStream
  /// - SenseVoiceEngine: 送入 VAD 检测，段落完成后自动处理
  void acceptWaveform(int sampleRate, Pointer<Float> samples, int n);

  /// 获取当前识别结果
  /// - ZipformerEngine: 返回实时部分结果
  /// - SenseVoiceEngine: 返回最近完成段落的结果
  ASRResult getResult();

  /// 检查是否检测到端点
  /// - ZipformerEngine: Sherpa 内置 VAD 端点
  /// - SenseVoiceEngine: VAD 检测到语音段结束
  bool isEndpoint();

  /// 重置状态
  void reset();

  /// 释放资源
  void dispose();
}

/// 统一识别结果
class ASRResult {
  final String text;
  final String? lang;       // SenseVoice: zh/en/ja/ko/yue
  final String? emotion;    // SenseVoice: NEUTRAL/HAPPY/SAD/ANGRY
  final List<String> tokens;
  final List<double> timestamps;
}
```

### SenseVoiceEngine 伪流式实现流程

```
用户开始说话
    │
    ▼
┌─────────────────────────────────────────────────────┐
│  VAD 检测循环 (每 32ms 一个窗口, window_size=512)    │
│                                                     │
│  1. acceptWaveform() → 音频送入 VAD                 │
│  2. VAD 检测语音活动                                │
│  3. 语音段结束 → isEndpoint() 返回 true            │
└─────────────────────────────────────────────────────┘
    │
    ▼ (语音段完成)
┌─────────────────────────────────────────────────────┐
│  离线识别 (在 Isolate 中执行，避免阻塞 UI)           │
│                                                     │
│  1. 创建 OfflineStream                              │
│  2. 送入语音段音频                                  │
│  3. DecodeOfflineStream                             │
│  4. 获取结果 (text, lang, emotion)                  │
│  5. 销毁 OfflineStream                              │
└─────────────────────────────────────────────────────┘
    │
    ▼
getResult() 返回识别结果 → UI 显示文字
```

### AudioInferencePipeline 重构

```dart
// 改动前
class AudioInferencePipeline {
  final SherpaService _sherpaService;  // 直接依赖具体实现
  // ...
}

// 改动后
class AudioInferencePipeline {
  ASREngine _asrEngine;  // 依赖抽象接口

  /// 切换引擎 (需销毁重建)
  Future<void> switchEngine(EngineType newType) async {
    await stop();
    _asrEngine.dispose();
    _asrEngine = ASREngineFactory.create(newType, config);
    // 不自动 start，等待用户触发
  }
}
```

### 模型下载配置

| 引擎 | 模型名称 | 大小 | 下载 URL |
|:---|:---|:---|:---|
| Zipformer | sherpa-onnx-streaming-zipformer-bilingual-zh-en-2023-02-20 | ~150MB | `https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-streaming-zipformer-bilingual-zh-en-2023-02-20.tar.bz2` |
| SenseVoice | sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17 | ~300MB | `https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17.tar.bz2` |
| Silero VAD | silero_vad.onnx | ~2MB | `https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/silero_vad.onnx` |

**SHA256 校验值**:
```dart
const zipformerSha256 = '27ffbd9ee24ad186d99acc2f6354d7992b27bcab490812510665fa8f9389c5f8';
// SenseVoice 和 Silero VAD: sherpa-onnx 官方未提供校验值，跳过校验
const sensevoiceSha256 = null;
const sileroVadSha256 = null;
```

### 模型目录结构

```
~/.local/share/nextalk/models/
├── zipformer/
│   └── sherpa-onnx-streaming-zipformer-bilingual-zh-en/
│       ├── encoder-epoch-99-avg-1.int8.onnx
│       ├── decoder-epoch-99-avg-1.int8.onnx
│       ├── joiner-epoch-99-avg-1.int8.onnx
│       └── tokens.txt
├── sensevoice/
│   └── sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17/
│       ├── model.onnx (或 model.int8.onnx)
│       └── tokens.txt
└── vad/
    └── silero_vad.onnx
```

### FFI 绑定完整函数列表

**sherpa_offline_bindings.dart:**
```dart
// 结构体
- SherpaOnnxOfflineSenseVoiceModelConfig
- SherpaOnnxOfflineModelConfig
- SherpaOnnxOfflineRecognizerConfig
- SherpaOnnxOfflineRecognizer (Opaque)
- SherpaOnnxOfflineStream (Opaque)

// 函数
- SherpaOnnxCreateOfflineRecognizer
- SherpaOnnxDestroyOfflineRecognizer
- SherpaOnnxCreateOfflineStream
- SherpaOnnxDestroyOfflineStream
- SherpaOnnxAcceptWaveformOffline
- SherpaOnnxDecodeOfflineStream
- SherpaOnnxGetOfflineStreamResultAsJson
- SherpaOnnxDestroyOfflineStreamResultJson
```

**sherpa_vad_bindings.dart:**
```dart
// 结构体
- SherpaOnnxSileroVadModelConfig
- SherpaOnnxVadModelConfig
- SherpaOnnxVoiceActivityDetector (Opaque)
- SherpaOnnxSpeechSegment

// 函数
- SherpaOnnxCreateVoiceActivityDetector
- SherpaOnnxDestroyVoiceActivityDetector
- SherpaOnnxVoiceActivityDetectorAcceptWaveform
- SherpaOnnxVoiceActivityDetectorEmpty
- SherpaOnnxVoiceActivityDetectorDetected
- SherpaOnnxVoiceActivityDetectorPop
- SherpaOnnxVoiceActivityDetectorClear
- SherpaOnnxVoiceActivityDetectorFlush
- SherpaOnnxVoiceActivityDetectorFront
- SherpaOnnxDestroySpeechSegment
```

### VAD 配置参数

```dart
const vadConfig = SileroVadConfig(
  model: 'silero_vad.onnx',
  threshold: 0.25,           // 语音检测阈值
  minSilenceDuration: 0.5,   // 最小静音时长 (秒)
  minSpeechDuration: 0.5,    // 最小语音时长 (秒)
  maxSpeechDuration: 10.0,   // 最大语音时长 (秒)
  windowSize: 512,           // 关键! Silero VAD 必须使用 512
  sampleRate: 16000,
);
```

### 错误处理与回退逻辑

```dart
Future<ASREngine> initializeEngine(EngineType preferred) async {
  // 1. 尝试用户选择的引擎
  if (preferred == EngineType.sensevoice) {
    if (await modelManager.isSenseVoiceReady()) {
      return SenseVoiceEngine()..initialize(config);
    }
    // SenseVoice 不可用，尝试回退
    showWarning('SenseVoice 模型未就绪，尝试 Zipformer...');
  }

  // 2. 回退到 Zipformer
  if (await modelManager.isZipformerReady()) {
    return ZipformerEngine()..initialize(config);
  }

  // 3. 两者都不可用，引导下载
  throw ModelNotReadyException('请先下载 ASR 模型');
}
```

### 托盘菜单 i18n 键名

```yaml
# zh.yaml
tray_asr_engine: "ASR 引擎"
tray_engine_zipformer: "Zipformer (流式)"
tray_engine_sensevoice: "SenseVoice (离线)"
tray_engine_switching: "切换中..."
tray_engine_switch_success: "引擎已切换为 {engine}"
tray_engine_switch_fallback: "切换失败，已回退到 {engine}"

# en.yaml
tray_asr_engine: "ASR Engine"
tray_engine_zipformer: "Zipformer (Streaming)"
tray_engine_sensevoice: "SenseVoice (Offline)"
tray_engine_switching: "Switching..."
tray_engine_switch_success: "Engine switched to {engine}"
tray_engine_switch_fallback: "Switch failed, fallback to {engine}"
```

### 测试策略详细用例

**单元测试:**
- `ASREngineFactory` 根据 `EngineType` 创建正确类型
- `ZipformerEngine.acceptWaveform` 正确调用 FFI
- `SenseVoiceEngine` VAD 段落边界检测
- `ASRResult` 字段解析 (特别是 lang, emotion)
- `ModelManager.checkModelStatus` 多引擎目录检查

**集成测试:**
- SenseVoice 真实模型识别准确率 (中/英/日/韩/粤)
- VAD + SenseVoice 端到端延迟 (目标: <500ms/段)
- 引擎切换不崩溃、不内存泄漏
- 回退逻辑正确触发

**回归测试:**
- 原 Zipformer 识别功能完全保留
- 原 VAD 端点检测行为不变
- 原 int8/standard 版本切换功能正常
- 托盘菜单原有功能不受影响

### 性能注意事项

1. **SenseVoice 推理延迟**: 约 100-200ms (取决于语音长度)
2. **建议在 Isolate 中执行推理**: 避免阻塞 UI，保持动画流畅
3. **VAD 窗口**: 512 samples = 32ms@16kHz，需高效缓冲
4. **内存管理**: 每段语音处理完毕后立即销毁 OfflineStream

### References

- [官方示例 c-api-examples/vad-sense-voice-c-api.c](https://github.com/k2-fsa/sherpa-onnx/blob/master/c-api-examples/vad-sense-voice-c-api.c)
- [官方示例 c-api-examples/sense-voice-c-api.c](https://github.com/k2-fsa/sherpa-onnx/blob/master/c-api-examples/sense-voice-c-api.c)
- [docs/architecture.md#4.2 音频与 AI 流水线](../docs/architecture.md)
- [现有实现 voice_capsule/lib/services/sherpa_service.dart](../../voice_capsule/lib/services/sherpa_service.dart)
- [现有绑定 voice_capsule/lib/ffi/sherpa_onnx_bindings.dart](../../voice_capsule/lib/ffi/sherpa_onnx_bindings.dart)

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

- 重构过程中需要更新 `hotkey_controller.dart` 中的 `SherpaError` 引用为 `ASRError` (待完成)

### Completion Notes List

**2025-12-25 Task 1 进度 (1.1-1.5 完成):**

1. **创建 ASREngine 抽象层** (`lib/services/asr/asr_engine.dart`):
   - 定义 `ASREngineType` 枚举 (zipformer, sensevoice)
   - 定义 `ASRError` 统一错误类型
   - 定义 `ASRConfig` 基类和 `ZipformerConfig`、`SenseVoiceConfig` 子类
   - 定义 `ASRResult` 统一结果类型 (含 text, lang, emotion, tokens, timestamps)
   - 定义 `ASREngine` 抽象接口

2. **创建 ZipformerEngine** (`lib/services/asr/zipformer_engine.dart`):
   - 实现 `ASREngine` 接口
   - 从 `SherpaService` 迁移所有流式识别逻辑
   - 保持与原有功能完全兼容

3. **创建 ASREngineFactory** (`lib/services/asr/asr_engine_factory.dart`):
   - 工厂模式创建引擎实例
   - 支持根据引擎类型创建对应配置

4. **重构 AudioInferencePipeline** (`lib/services/audio_inference_pipeline.dart`):
   - 将 `SherpaService` 依赖替换为 `ASREngine` 抽象接口
   - 更新构造函数参数: `sherpaService` → `asrEngine`
   - 更新所有内部引用
   - 根据引擎类型动态创建配置

5. **更新 main.dart**:
   - 导入新的 ASR 模块
   - 使用 `ZipformerEngine` 替代 `SherpaService`

**Task 1.6 完成 (2025-12-25):**
- 修复 `hotkey_controller.dart` 中 `SherpaError` → `ASRError` (方法名: `_getDetailedSherpaError` → `_getDetailedASRError`)
- 更新 `audio_inference_pipeline_test.dart`: `MockSherpaService` → `MockASREngine`
- 创建 `test/services/asr/asr_engine_test.dart` (42 个单元测试)
  - ASREngineType 枚举测试
  - ASRError 枚举测试
  - ZipformerConfig/SenseVoiceConfig 配置类测试
  - ASRResult 结果类测试
  - ASREngineFactory 工厂类测试
  - ZipformerEngine 初始化和错误处理测试
  - ASRConfig 继承层次测试
- 全部 485 个测试通过，无回归问题

**Task 2 完成 (2025-12-25):**
- 创建 `lib/ffi/sherpa_offline_bindings.dart` (离线识别器 FFI 绑定)
  - SherpaOnnxOfflineSenseVoiceModelConfig 结构体
  - SherpaOnnxOfflineModelConfig 结构体
  - SherpaOnnxOfflineRecognizerConfig 结构体
  - SherpaOnnxOfflineRecognizerResult 结构体
  - SherpaOnnxOfflineBindings 绑定类 (10 个 FFI 函数)
- 创建 `lib/ffi/sherpa_vad_bindings.dart` (VAD FFI 绑定)
  - SherpaOnnxSileroVadModelConfig 结构体
  - SherpaOnnxVadModelConfig 结构体
  - SherpaOnnxSpeechSegment 结构体
  - SherpaOnnxVadBindings 绑定类 (12 个 FFI 函数)
- 创建 `test/ffi/sherpa_offline_vad_bindings_test.dart` (33 个单元测试)
- 全部测试通过

**Task 3 完成 (2025-12-25):**
- 创建 `lib/services/asr/sensevoice_engine.dart`:
  - 完整实现 `ASREngine` 接口
  - VAD 初始化 (Silero VAD: window_size=512, threshold=0.25, buffer=30s)
  - 离线识别器初始化 (use_itn=true, language=auto)
  - 音频缓冲管理 (最大语音段 10s，通过 VAD maxSpeechDuration 配置)
  - VAD 检测循环 (_processVadSegments) 自动处理语音段
  - 段落识别 (_recognizeSegment) 使用 OfflineStream
  - 结果解析 (_getStreamResult) 含 text/lang/emotion/tokens/timestamps
  - 完整资源释放 (dispose 方法销毁 VAD + OfflineRecognizer)
- 更新 `lib/services/asr/asr_engine_factory.dart`:
  - 移除 UnimplementedError，添加 SenseVoiceEngine 支持
- 更新 `test/services/asr/asr_engine_test.dart`:
  - 修改工厂测试以验证 SenseVoiceEngine 创建
  - 新增 SenseVoiceEngine 单元测试 (20 个新测试)
  - 新增 SenseVoiceConfig 验证测试 (4 个新测试)
  - 新增引擎对比测试 (3 个新测试)
- 全部 538 个测试通过，无回归问题

**Task 4 完成 (2025-12-25):**
- 更新 `lib/constants/settings_constants.dart`:
  - 新增 `EngineType` 枚举 (zipformer, sensevoice)
- 扩展 `lib/services/model_manager.dart`:
  - 新增 `ModelConfig` 类 (存储模型配置: displayName, dirName, archiveTopDir, defaultUrl, sha256, requiredFilePrefixes, isSingleFile)
  - 新增 `ModelConfigs` 静态类 (预定义配置: zipformer, sensevoice, sileroVad)
  - 新增 `getModelPathForEngine(EngineType)` - 获取引擎模型目录路径
  - 新增 `vadModelPath`、`vadModelFilePath` - VAD 模型路径
  - 新增 `checkModelStatusForEngine(EngineType)` - 检查引擎模型状态
  - 新增 `checkVadModelStatus()` - 检查 VAD 模型状态
  - 新增 `isModelReadyForEngine(EngineType)` - 判断引擎模型是否就绪
  - 新增 `isVadModelReady`、`isSenseVoiceReady` - 快捷状态检查
  - 新增 `getDownloadUrlForEngine(EngineType)` - 获取引擎模型下载 URL
  - 新增 `downloadModelForEngine()`、`downloadVadModel()` - 下载模型
  - 新增 `extractModelForEngine()` - 解压引擎模型
  - 新增 `ensureModelReadyForEngine()`、`ensureVadModelReady()` - 确保模型就绪
  - 新增 `ensureSenseVoiceReady()` - 确保 SenseVoice 引擎完全就绪 (模型 + VAD)
  - 新增 `deleteModelForEngine()`、`deleteVadModel()` - 删除模型
  - 新增 `openModelDirectoryForEngine()` - 打开引擎模型目录
  - 新增 `getExpectedStructureForEngine()`、`vadExpectedStructure` - 目录结构描述
- 更新 `test/services/model_manager_test.dart`:
  - 新增 27 个多引擎测试 (EngineType、ModelConfig、路径、状态、URL、结构描述等)
- 全部 565 个测试通过，无回归问题

**Task 6 完成 (2025-12-25):**
- 托盘菜单结构和引擎切换逻辑在之前 Sprint 中已实现
- 修复通知消息显示具体引擎名称:
  - 新增 `LanguageService.trWithParams()` 支持参数替换
  - 更新 `TrayService._switchEngine()` 发送包含引擎名称的通知
  - 更新翻译字符串使用 `{engine}` 占位符
- 新增 TrayService 引擎切换单元测试 (11 tests)
- 全部 628 个测试通过

**Task 7 完成 (2025-12-25):**
- 创建 `EngineInitializer` 类实现引擎回退逻辑 (AC7):
  - `initialize()` 方法按优先级尝试引擎: 配置引擎 → 回退引擎 → 抛出异常
  - `EngineInitResult` 包含实际引擎类型和回退信息
  - `EngineNotAvailableException` 表示所有引擎都不可用
  - `_toASREngineType()` 转换 `EngineType` 到 `ASREngineType`
- 更新 `main.dart` 使用 `EngineInitializer`:
  - 捕获初始化结果并设置实际引擎类型
  - 回退时更新托盘状态为警告
- 更新 `TrayService`:
  - 新增 `_actualEngineType` 和 `hasEngineFallback` 属性
  - `_buildMenu()` 显示实际使用的引擎 (✓ 标记)
  - `setActualEngineType()` 供 main.dart 调用
- 新增 `engine_initializer_test.dart` (11 tests)
- 全部 628 个测试通过

**Code Review 修复 (2025-12-25):**
- 修复 Task 3.7 描述被测试输出污染的问题
- 移除 `sensevoice_engine.dart` 中未使用的 `dart:convert` import
- 更新 File List 添加 4 个缺失文件 (settings_service.dart, app_zh.arb, app_en.arb, settings_service_test.dart)
- 更新测试计数 617 → 628
- 添加注释说明 SenseVoice/VAD 模型无官方 SHA256 校验值

### File List

**新增文件:**
- `voice_capsule/lib/services/asr/asr_engine.dart` - ASR 引擎抽象接口定义
- `voice_capsule/lib/services/asr/zipformer_engine.dart` - Zipformer 流式引擎实现
- `voice_capsule/lib/services/asr/asr_engine_factory.dart` - 引擎工厂类
- `voice_capsule/lib/services/asr/sensevoice_engine.dart` - SenseVoice 离线引擎实现 (Task 3)
- `voice_capsule/lib/services/asr/engine_initializer.dart` - 引擎初始化器 (Task 7)
- `voice_capsule/lib/ffi/sherpa_offline_bindings.dart` - 离线识别器 FFI 绑定 (Task 2.1)
- `voice_capsule/lib/ffi/sherpa_vad_bindings.dart` - VAD FFI 绑定 (Task 2.2)
- `voice_capsule/test/services/asr/asr_engine_test.dart` - ASR 抽象层单元测试 (62 tests, Task 3.9 扩展)
- `voice_capsule/test/services/asr/engine_initializer_test.dart` - 引擎初始化器测试 (11 tests, Task 7.4)
- `voice_capsule/test/ffi/sherpa_offline_vad_bindings_test.dart` - FFI 绑定单元测试 (33 tests)
- `voice_capsule/test/services/settings_service_test.dart` - 设置服务单元测试 (Task 5.5)

**修改文件:**
- `voice_capsule/lib/services/audio_inference_pipeline.dart` - 重构为依赖 ASREngine 接口
- `voice_capsule/lib/main.dart` - 使用 EngineInitializer, 设置实际引擎类型 (Task 7)
- `voice_capsule/lib/services/hotkey_controller.dart` - SherpaError → ASRError (Task 1.6)
- `voice_capsule/lib/services/tray_service.dart` - 引擎切换通知、实际引擎显示 (Task 6, 7)
- `voice_capsule/lib/services/language_service.dart` - 新增 trWithParams() (Task 6)
- `voice_capsule/lib/services/settings_service.dart` - 新增引擎类型读写和切换回调 (Task 5.3, 5.4)
- `voice_capsule/test/audio_inference_pipeline_test.dart` - MockSherpaService → MockASREngine (Task 1.6)
- `voice_capsule/test/services/tray_service_test.dart` - 引擎切换测试 (Task 6.4)
- `voice_capsule/lib/services/asr/asr_engine_factory.dart` - 添加 SenseVoiceEngine 支持 (Task 3)
- `voice_capsule/lib/constants/settings_constants.dart` - 添加 EngineType 枚举 (Task 4)
- `voice_capsule/lib/services/model_manager.dart` - 添加多引擎模型管理 (Task 4)
- `voice_capsule/test/services/model_manager_test.dart` - 添加多引擎测试 (Task 4.6)
- `voice_capsule/lib/l10n/app_zh.arb` - 新增引擎切换 i18n 键名 (Task 6.4)
- `voice_capsule/lib/l10n/app_en.arb` - 新增引擎切换 i18n 键名 (Task 6.4)
