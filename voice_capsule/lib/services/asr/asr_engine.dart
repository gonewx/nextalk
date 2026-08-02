import 'dart:ffi';

/// ASR 引擎类型枚举
enum ASREngineType {
  /// Zipformer 流式引擎 (边听边识别，低延迟)
  zipformer,

  /// SenseVoice 离线引擎 (VAD 分段后识别，高精度)
  sensevoice,
}

/// ASR 引擎错误类型
enum ASRError {
  /// 无错误
  none,

  /// 库加载失败
  libraryLoadFailed,

  /// 模型目录不存在
  modelNotFound,

  /// 模型文件缺失
  modelFileMissing,

  /// 创建识别器失败
  recognizerCreateFailed,

  /// 创建流失败
  streamCreateFailed,

  /// 服务未初始化
  notInitialized,

  /// VAD 初始化失败 (仅 SenseVoice)
  vadInitFailed,

  /// 配置错误
  invalidConfig,
}

/// ASR 引擎配置基类
abstract class ASRConfig {
  /// 模型目录路径
  final String modelDir;

  /// 线程数
  final int numThreads;

  /// 采样率
  final int sampleRate;

  const ASRConfig({
    required this.modelDir,
    this.numThreads = 2,
    this.sampleRate = 16000,
  });
}

/// Zipformer 引擎配置
class ZipformerConfig extends ASRConfig {
  /// 是否使用 int8 量化模型
  final bool useInt8Model;

  /// 特征维度
  final int featureDim;

  /// 是否启用端点检测
  final bool enableEndpoint;

  /// 规则1: 短停顿阈值 (秒)
  final double rule1MinTrailingSilence;

  /// 规则2: 长停顿阈值 (秒)
  final double rule2MinTrailingSilence;

  /// 规则3: 最小语句长度 (秒)
  final double rule3MinUtteranceLength;

  /// 解码方法
  final String decodingMethod;

  /// provider
  final String provider;

  const ZipformerConfig({
    required super.modelDir,
    super.numThreads = 2,
    super.sampleRate = 16000,
    this.useInt8Model = true,
    this.featureDim = 80,
    this.enableEndpoint = true,
    this.rule1MinTrailingSilence = 2.4,
    this.rule2MinTrailingSilence = 1.2,
    this.rule3MinUtteranceLength = 20.0,
    this.decodingMethod = 'greedy_search',
    this.provider = 'cpu',
  });

  @override
  String toString() {
    return 'ZipformerConfig(modelDir: $modelDir, useInt8Model: $useInt8Model, '
        'numThreads: $numThreads, sampleRate: $sampleRate, enableEndpoint: $enableEndpoint)';
  }
}

/// SenseVoice 引擎配置
class SenseVoiceConfig extends ASRConfig {
  /// VAD 模型路径
  final String vadModelPath;

  /// 是否启用 ITN (Inverse Text Normalization)
  final bool useItn;

  /// 语言设置 (auto, zh, en, ja, ko, yue)
  final String language;

  /// VAD 阈值
  final double vadThreshold;

  /// 最小静音时长 (秒)
  final double minSilenceDuration;

  /// 最小语音时长 (秒)
  final double minSpeechDuration;

  /// 最大语音时长 (秒)
  final double maxSpeechDuration;

  /// VAD 窗口大小 (Silero VAD 必须为 512)
  final int vadWindowSize;

  /// provider
  final String provider;

  const SenseVoiceConfig({
    required super.modelDir,
    required this.vadModelPath,
    super.numThreads = 2,
    super.sampleRate = 16000,
    this.useItn = true,
    this.language = 'auto',
    this.vadThreshold = 0.25,
    this.minSilenceDuration = 0.5,
    this.minSpeechDuration = 0.5,
    this.maxSpeechDuration = 10.0,
    this.vadWindowSize = 512,
    this.provider = 'cpu',
  });

  @override
  String toString() {
    return 'SenseVoiceConfig(modelDir: $modelDir, vadModelPath: $vadModelPath, '
        'useItn: $useItn, language: $language)';
  }
}

/// 统一 ASR 识别结果
///
/// 适用于所有 ASR 引擎的统一结果格式。
/// - Zipformer: text, tokens, timestamps 有效
/// - SenseVoice: text, lang, emotion, tokens, timestamps 有效
class ASRResult {
  /// 识别文本
  final String text;

  /// 语言标识 (SenseVoice: zh/en/ja/ko/yue, Zipformer: null)
  final String? lang;

  /// 情感标识 (SenseVoice: NEUTRAL/HAPPY/SAD/ANGRY, Zipformer: null)
  final String? emotion;

  /// token 列表
  final List<String> tokens;

  /// 时间戳列表
  final List<double> timestamps;

  const ASRResult({
    required this.text,
    this.lang,
    this.emotion,
    this.tokens = const [],
    this.timestamps = const [],
  });

  /// 创建空结果
  factory ASRResult.empty() => const ASRResult(text: '');

  /// 是否为空结果
  bool get isEmpty => text.isEmpty;

  /// 是否非空
  bool get isNotEmpty => text.isNotEmpty;

  @override
  String toString() =>
      'ASRResult(text: "$text", lang: $lang, emotion: $emotion)';

  @override
  bool operator ==(Object other) {
    if (identical(this, other)) return true;
    return other is ASRResult &&
        other.text == text &&
        other.lang == lang &&
        other.emotion == emotion;
  }

  @override
  int get hashCode => Object.hash(text, lang, emotion);
}

/// ASR 引擎抽象接口
///
/// 定义所有 ASR 引擎的统一接口，支持：
/// - ZipformerEngine: 流式识别，边听边输出
/// - SenseVoiceEngine: VAD 分段后离线识别
abstract class ASREngine {
  /// 引擎类型
  ASREngineType get engineType;

  /// 是否已初始化
  bool get isInitialized;

  /// 最近一次错误
  ASRError get lastError;

  /// 初始化引擎
  ///
  /// [config] 引擎配置 (ZipformerConfig 或 SenseVoiceConfig)
  /// 返回错误类型，[ASRError.none] 表示成功
  Future<ASRError> initialize(ASRConfig config);

  /// 送入音频数据 (零拷贝)
  ///
  /// [sampleRate] 采样率 (应为 16000)
  /// [samples] 音频样本指针 (Float32, 值域 [-1.0, 1.0])
  /// [n] 样本数量
  ///
  /// - ZipformerEngine: 直接送入 OnlineStream
  /// - SenseVoiceEngine: 送入 VAD 检测，段落完成后自动处理
  void acceptWaveform(int sampleRate, Pointer<Float> samples, int n);

  /// 执行解码 (仅 Zipformer 使用)
  ///
  /// SenseVoice 引擎可以空实现，因为解码在段落完成时自动执行。
  void decode();

  /// 检查是否准备好解码 (仅 Zipformer 使用)
  ///
  /// SenseVoice 引擎始终返回 false。
  bool isReady();

  /// 获取当前识别结果
  ///
  /// - ZipformerEngine: 返回实时部分结果
  /// - SenseVoiceEngine: 返回最近完成段落的结果
  ASRResult getResult();

  /// 检查是否检测到端点
  ///
  /// - ZipformerEngine: Sherpa 内置 VAD 端点
  /// - SenseVoiceEngine: VAD 检测到语音段结束
  bool isEndpoint();

  /// 重置识别状态 (清空缓冲区，保留模型)
  void reset();

  /// 结束当前这一次发话，返回包含尾部内容的最终结果。
  ///
  /// 调用方须在一次发话结束时调用且仅调用一次；返回后引擎可安全接收下一次发话。
  ///
  /// 实现契约:
  /// - 必须保证音频末尾的内容被完整解码后才返回结果
  /// - 必须使引擎与上一次发话隔离，不得把残留内容带入下一次发话
  ///
  /// 各引擎语义差异:
  /// - ZipformerEngine: 流式 transducer 的 `IsReady()` 判定为
  ///   `已处理帧 + ChunkSize < 就绪帧`，不检查输入是否结束，因此末尾不足一个
  ///   chunk 的尾帧永远进不了解码循环。实现方式为补静音 padding 把尾音顶过
  ///   chunk 边界，解码后重建 OnlineStream 隔离会话。
  /// - SenseVoiceEngine: 离线引擎，flush VAD 并处理最后一个语音段。
  ASRResult finalizeUtterance();

  /// 确保流就绪，必要时恢复。
  ///
  /// 偶发的流创建/重建失败（如内存碎片导致 FFI 返回 null）不应使引擎
  /// 永久静默失效。调用方在每次发话 [start] 前调用，若流已被上一次
  /// [finalizeUtterance] 重建成功则立刻返回 `true`；若处于恢复待决
  /// 状态则重试一次。
  ///
  /// 返回 `true` 表示流已准备好接受音频输入。
  bool ensureStreamReady();

  /// 标记输入结束
  ///
  /// 对流式 transducer (Zipformer) 是**空操作**: 上游 `IsReady()` 不检查
  /// `input_finished_`，调用后不会多解出任何内容。收尾请改用
  /// [finalizeUtterance]，它按引擎语义正确处理尾帧。
  @Deprecated('收尾请使用 finalizeUtterance()，它对流式引擎才真正有效')
  void inputFinished();

  /// 释放资源
  void dispose();
}
