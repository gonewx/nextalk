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

  /// 标记输入结束
  void inputFinished();

  /// 释放资源
  void dispose();
}
