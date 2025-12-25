import 'dart:io';

import 'package:flutter/foundation.dart';

import '../../constants/settings_constants.dart';
import '../language_service.dart';
import '../model_manager.dart';
import '../settings_service.dart';
import '../tray_service.dart';
import 'asr_engine.dart';
import 'asr_engine_factory.dart';

/// Story 2-7: 引擎初始化结果
class EngineInitResult {
  /// 初始化的引擎实例
  final ASREngine engine;

  /// 实际使用的引擎类型 (可能与配置不同)
  final EngineType actualEngineType;

  /// 是否发生了回退
  final bool fallbackOccurred;

  /// 回退原因 (如果发生回退)
  final String? fallbackReason;

  /// 配置的引擎类型
  final EngineType configuredEngineType;

  const EngineInitResult({
    required this.engine,
    required this.actualEngineType,
    required this.configuredEngineType,
    this.fallbackOccurred = false,
    this.fallbackReason,
  });
}

/// Story 2-7: 引擎初始化异常 (所有引擎都不可用)
class EngineNotAvailableException implements Exception {
  final String message;
  final List<String> triedEngines;

  const EngineNotAvailableException(this.message, this.triedEngines);

  @override
  String toString() => 'EngineNotAvailableException: $message';
}

/// Story 2-7: 引擎初始化器 (AC7: 错误处理与回退)
///
/// 按优先级初始化引擎: SenseVoice → Zipformer → 抛出异常
/// 回退时更新托盘状态为警告，并通知用户
class EngineInitializer {
  final ModelManager _modelManager;

  EngineInitializer(this._modelManager);

  /// 初始化引擎 (带回退逻辑)
  ///
  /// [preferredType] 优先使用的引擎类型 (来自配置)
  /// [enableDebugLog] 是否启用调试日志
  ///
  /// 返回初始化结果，包含实际使用的引擎和是否发生回退
  /// 如果所有引擎都不可用，抛出 [EngineNotAvailableException]
  Future<EngineInitResult> initialize({
    required EngineType preferredType,
    bool enableDebugLog = false,
  }) async {
    final triedEngines = <String>[];

    // 1. 尝试用户配置的引擎
    debugPrint('[EngineInitializer] 尝试初始化配置的引擎: $preferredType');
    final preferredResult = await _tryInitializeEngine(
      preferredType,
      enableDebugLog: enableDebugLog,
    );

    if (preferredResult != null) {
      debugPrint('[EngineInitializer] ✓ 配置的引擎初始化成功: $preferredType');
      return EngineInitResult(
        engine: preferredResult,
        actualEngineType: preferredType,
        configuredEngineType: preferredType,
        fallbackOccurred: false,
      );
    }

    triedEngines.add(preferredType.name);
    debugPrint('[EngineInitializer] ✗ 配置的引擎不可用: $preferredType');

    // 2. 回退到其他引擎
    final fallbackType = _getFallbackEngine(preferredType);
    debugPrint('[EngineInitializer] 尝试回退到: $fallbackType');

    final fallbackResult = await _tryInitializeEngine(
      fallbackType,
      enableDebugLog: enableDebugLog,
    );

    if (fallbackResult != null) {
      debugPrint('[EngineInitializer] ✓ 回退引擎初始化成功: $fallbackType');

      // 更新托盘状态为警告
      await _notifyFallback(preferredType, fallbackType);

      return EngineInitResult(
        engine: fallbackResult,
        actualEngineType: fallbackType,
        configuredEngineType: preferredType,
        fallbackOccurred: true,
        fallbackReason: _getModelNotReadyReason(preferredType),
      );
    }

    triedEngines.add(fallbackType.name);
    debugPrint('[EngineInitializer] ✗ 回退引擎也不可用: $fallbackType');

    // 3. 所有引擎都不可用
    throw EngineNotAvailableException(
      '没有可用的 ASR 引擎，请先下载模型',
      triedEngines,
    );
  }

  /// 尝试初始化指定引擎
  Future<ASREngine?> _tryInitializeEngine(
    EngineType type, {
    bool enableDebugLog = false,
  }) async {
    // 检查模型是否就绪
    final isReady = _isEngineModelReady(type);
    if (!isReady) {
      debugPrint('[EngineInitializer] 引擎 $type 模型未就绪');
      return null;
    }

    // 创建引擎实例
    try {
      final asrType = _toASREngineType(type);
      final engine = ASREngineFactory.create(asrType, enableDebugLog: enableDebugLog);
      return engine;
    } catch (e) {
      debugPrint('[EngineInitializer] 创建引擎 $type 失败: $e');
      return null;
    }
  }

  /// 将 EngineType 转换为 ASREngineType
  ASREngineType _toASREngineType(EngineType type) {
    return switch (type) {
      EngineType.zipformer => ASREngineType.zipformer,
      EngineType.sensevoice => ASREngineType.sensevoice,
    };
  }

  /// 检查引擎模型是否就绪
  bool _isEngineModelReady(EngineType type) {
    switch (type) {
      case EngineType.zipformer:
        return _modelManager.isModelReadyForEngine(EngineType.zipformer);
      case EngineType.sensevoice:
        // SenseVoice 需要模型 + VAD
        return _modelManager.isSenseVoiceReady;
    }
  }

  /// 获取回退引擎类型
  EngineType _getFallbackEngine(EngineType preferred) {
    // 如果配置的是 SenseVoice，回退到 Zipformer
    // 如果配置的是 Zipformer，回退到 SenseVoice
    return preferred == EngineType.sensevoice
        ? EngineType.zipformer
        : EngineType.sensevoice;
  }

  /// 获取模型未就绪的原因描述
  String _getModelNotReadyReason(EngineType type) {
    switch (type) {
      case EngineType.zipformer:
        return 'Zipformer 模型未下载或不完整';
      case EngineType.sensevoice:
        final modelReady = _modelManager.isModelReadyForEngine(EngineType.sensevoice);
        final vadReady = _modelManager.isVadModelReady;
        if (!modelReady && !vadReady) {
          return 'SenseVoice 模型和 VAD 模型都未下载';
        } else if (!modelReady) {
          return 'SenseVoice 模型未下载或不完整';
        } else {
          return 'VAD 模型未下载';
        }
    }
  }

  /// 通知回退发生 (更新托盘状态 + 发送通知)
  Future<void> _notifyFallback(EngineType preferred, EngineType actual) async {
    // 更新托盘状态为警告 (AC7: 状态指示器显示警告)
    await TrayService.instance.updateStatus(TrayStatus.warning);

    // 发送桌面通知
    final lang = LanguageService.instance;
    final actualName = _getEngineDisplayName(actual);
    final message = lang.trWithParams(
      'tray_engine_switch_fallback',
      {'engine': actualName},
    );

    try {
      await _sendNotification(message);
    } catch (e) {
      debugPrint('[EngineInitializer] 发送通知失败: $e');
    }
  }

  /// 获取引擎显示名称
  String _getEngineDisplayName(EngineType type) {
    final lang = LanguageService.instance;
    return switch (type) {
      EngineType.zipformer => lang.tr('tray_engine_zipformer'),
      EngineType.sensevoice => lang.tr('tray_engine_sensevoice'),
    };
  }

  /// 发送桌面通知
  Future<void> _sendNotification(String message) async {
    await Process.run('notify-send', [
      '-a',
      'Nextalk',
      '-i',
      'dialog-warning',
      'Nextalk',
      message,
    ]);
  }

  /// 检查所有引擎模型状态
  Map<EngineType, bool> checkAllEnginesStatus() {
    return {
      EngineType.zipformer: _modelManager.isModelReadyForEngine(EngineType.zipformer),
      EngineType.sensevoice: _modelManager.isSenseVoiceReady,
    };
  }

  /// 获取第一个可用的引擎类型 (不创建实例)
  EngineType? getFirstAvailableEngine() {
    // 按默认优先级: SenseVoice → Zipformer
    if (_modelManager.isSenseVoiceReady) {
      return EngineType.sensevoice;
    }
    if (_modelManager.isModelReadyForEngine(EngineType.zipformer)) {
      return EngineType.zipformer;
    }
    return null;
  }
}

