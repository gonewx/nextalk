import 'asr_engine.dart';
import 'sensevoice_engine.dart';
import 'zipformer_engine.dart';

/// ASR 引擎工厂
///
/// 根据引擎类型创建对应的 ASR 引擎实例。
class ASREngineFactory {
  ASREngineFactory._();

  /// 创建 ASR 引擎
  ///
  /// [engineType] 引擎类型
  /// [enableDebugLog] 是否启用调试日志
  ///
  /// 返回对应类型的 ASR 引擎实例
  static ASREngine create(
    ASREngineType engineType, {
    bool enableDebugLog = false,
  }) {
    switch (engineType) {
      case ASREngineType.zipformer:
        return ZipformerEngine(enableDebugLog: enableDebugLog);
      case ASREngineType.sensevoice:
        return SenseVoiceEngine(enableDebugLog: enableDebugLog);
    }
  }

  /// 根据引擎类型创建对应的配置
  ///
  /// [engineType] 引擎类型
  /// [modelDir] 模型目录
  /// [vadModelPath] VAD 模型路径 (仅 SenseVoice 需要)
  /// [useInt8Model] 是否使用 int8 模型 (仅 Zipformer)
  /// [enableEndpoint] 是否启用端点检测 (仅 Zipformer)
  /// [rule2MinTrailingSilence] VAD 静音阈值 (仅 Zipformer)
  static ASRConfig createConfig(
    ASREngineType engineType, {
    required String modelDir,
    String? vadModelPath,
    bool useInt8Model = true,
    bool enableEndpoint = true,
    double rule2MinTrailingSilence = 1.2,
    bool useItn = true,
    String language = 'auto',
  }) {
    switch (engineType) {
      case ASREngineType.zipformer:
        return ZipformerConfig(
          modelDir: modelDir,
          useInt8Model: useInt8Model,
          enableEndpoint: enableEndpoint,
          rule2MinTrailingSilence: rule2MinTrailingSilence,
        );
      case ASREngineType.sensevoice:
        if (vadModelPath == null) {
          throw ArgumentError('SenseVoice 引擎需要 vadModelPath');
        }
        return SenseVoiceConfig(
          modelDir: modelDir,
          vadModelPath: vadModelPath,
          useItn: useItn,
          language: language,
        );
    }
  }
}
