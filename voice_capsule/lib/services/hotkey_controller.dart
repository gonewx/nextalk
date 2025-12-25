import 'dart:async';

import 'asr/asr_engine.dart';
import 'audio_inference_pipeline.dart';
import 'tray_service.dart';
import 'window_service.dart';
import 'fcitx_client.dart';
import 'hotkey_service.dart';
import '../state/capsule_state.dart';

/// 快捷键控制器状态
enum HotkeyState {
  idle, // 空闲 (窗口隐藏)
  recording, // 录音中 (窗口显示，红灯呼吸)
  submitting, // 提交中 (处理文本上屏)
}

/// 快捷键业务控制器 - Story 3-5 (重构版)
///
/// 协调快捷键事件与各服务的交互:
/// - CommandServer: 接收来自 Fcitx5 插件的快捷键命令
/// - HotkeyService: 加载配置并同步到 Fcitx5
/// - WindowService: 控制窗口显隐
/// - AudioInferencePipeline: 控制录音和识别
/// - FcitxClient: 提交文本
/// - CapsuleStateData: 更新 UI 状态
///
/// 状态机:
/// ```
/// [Idle] ──(RightAlt)──> [Recording] ──(RightAlt)──> [Submitting]
///   ^                          |                          |
///   |                          | (VAD 触发)               |
///   └──────────────────────────┴──────────────────────────┘
/// ```
class HotkeyController {
  HotkeyController._();
  static final HotkeyController instance = HotkeyController._();

  // === 依赖服务 ===
  AudioInferencePipeline? _pipeline;
  FcitxClient? _fcitxClient;
  StreamController<CapsuleStateData>? _stateController;

  // === 状态管理 ===
  HotkeyState _state = HotkeyState.idle;
  StreamSubscription<EndpointEvent>? _endpointSubscription;
  StreamSubscription<String>? _resultSubscription;
  bool _isInitialized = false;

  /// Story 3-7: 保存提交失败的文本 (AC15: 文本保护)
  String? _lastRecognizedText;

  /// 当前状态
  HotkeyState get state => _state;

  /// 是否已初始化
  bool get isInitialized => _isInitialized;

  /// Story 3-7: 获取保存的文本 (用于复制/重试)
  String? get preservedText => _lastRecognizedText;

  // ===== 公开的控制方法 (供 CommandServer 调用) =====

  /// 切换录音状态 (模拟快捷键按下)
  ///
  /// 供 Fcitx5 插件通过 CommandServer 触发
  Future<void> toggle() async {
    await _onHotkeyPressed();
  }

  /// 显示窗口并开始录音
  Future<void> show() async {
    if (_state == HotkeyState.idle) {
      await _startRecording();
    }
  }

  /// 隐藏窗口
  Future<void> hide() async {
    if (_state == HotkeyState.recording) {
      await _stopAndSubmit();
    } else if (_state == HotkeyState.idle && WindowService.instance.isVisible) {
      await WindowService.instance.hide();
      _updateState(CapsuleStateData.idle());
    }
  }

  /// Story 3-7: 重试提交保存的文本 (AC15)
  Future<void> retrySubmit() async {
    if (_lastRecognizedText == null || _lastRecognizedText!.isEmpty) return;

    _state = HotkeyState.submitting;
    _updateState(CapsuleStateData.processing());

    await _submitText(_lastRecognizedText!);

    // 如果提交成功，隐藏窗口
    if (_lastRecognizedText == null) {
      await WindowService.instance.hide();
      _state = HotkeyState.idle;
      _updateState(CapsuleStateData.idle());
      // 恢复托盘图标为正常状态
      TrayService.instance.updateStatus(TrayStatus.normal);
    }
  }

  /// Story 3-7: 放弃保存的文本并隐藏窗口
  Future<void> discardPreservedText() async {
    _lastRecognizedText = null;
    await WindowService.instance.hide();
    _state = HotkeyState.idle;
    _updateState(CapsuleStateData.idle());
    // 恢复托盘图标为正常状态
    TrayService.instance.updateStatus(TrayStatus.normal);
  }

  /// Story 3-7: 清除错误状态并隐藏窗口
  Future<void> dismissError() async {
    _lastRecognizedText = null;
    await WindowService.instance.hide();
    _state = HotkeyState.idle;
    _updateState(CapsuleStateData.idle());
    // 恢复托盘图标为正常状态
    TrayService.instance.updateStatus(TrayStatus.normal);
  }

  /// Story 3-7: 重试录音 (AC10: 错误状态下的恢复操作)
  /// 保持窗口显示，重新尝试开始录音
  Future<void> retryRecording() async {
    _lastRecognizedText = null;
    _state = HotkeyState.idle;
    // 恢复托盘图标为正常状态
    TrayService.instance.updateStatus(TrayStatus.normal);

    // 重新开始录音流程
    await _startRecording();
  }

  /// 初始化控制器
  ///
  /// 必须在所有依赖服务初始化后调用。
  /// [pipeline] 音频推理流水线 (已初始化模型)
  /// [fcitxClient] Fcitx5 客户端
  /// [stateController] 胶囊状态控制器 (用于更新 UI)
  Future<void> initialize({
    required AudioInferencePipeline pipeline,
    required FcitxClient fcitxClient,
    required StreamController<CapsuleStateData> stateController,
  }) async {
    if (_isInitialized) return;

    _pipeline = pipeline;
    _fcitxClient = fcitxClient;
    _stateController = stateController;

    // 注册快捷键回调
    HotkeyService.instance.onHotkeyPressed = _onHotkeyPressed;

    // 监听 VAD 端点事件 (自动提交)
    _endpointSubscription = _pipeline!.endpointStream.listen(_onEndpoint);

    // 监听识别结果 (更新 UI)
    _resultSubscription = _pipeline!.resultStream.listen(_onRecognitionResult);

    _isInitialized = true;

    // ignore: avoid_print
    print('[HotkeyController] ✅ 控制器初始化完成');
  }

  /// 快捷键按下处理 (核心状态机)
  ///
  /// AC1: 按下 Right Alt 键时主窗口瞬间出现
  /// AC2: 按下 Right Alt 键时自动开始录音
  /// AC3: 正在录音时再次按下 Right Alt 立即停止录音
  Future<void> _onHotkeyPressed() async {
    // ignore: avoid_print
    print('[HotkeyController] 快捷键按下，当前状态: $_state');

    switch (_state) {
      case HotkeyState.idle:
        await _startRecording();
        break;
      case HotkeyState.recording:
        await _stopAndSubmit();
        break;
      case HotkeyState.submitting:
        // 正在提交中，忽略按键
        break;
    }
  }

  /// 开始录音 (Idle -> Recording)
  ///
  /// AC1: 窗口瞬间出现
  /// AC2: 自动开始录音
  Future<void> _startRecording() async {
    _state = HotkeyState.recording;

    // 1. 先更新 UI 状态为聆听中 (确保呼吸灯渲染就绪)
    _updateState(CapsuleStateData.listening());

    // 2. 显示窗口 (AC1: 瞬间出现)
    await WindowService.instance.show();

    // 3. 启动录音流水线 (AC2)
    final error = await _pipeline!.start();

    if (error != PipelineError.none) {
      // 录音启动失败，显示错误
      _handleError(error);
      return;
    }

    // ignore: avoid_print
    print('[HotkeyController] 🎤 开始录音');
  }

  /// 停止录音并提交 (Recording -> Submitting -> Idle)
  ///
  /// AC3: 立即停止录音
  /// AC4: 提交文本到活动窗口
  /// AC5: 提交后主窗口瞬间隐藏
  Future<void> _stopAndSubmit() async {
    _state = HotkeyState.submitting;

    // 1. 更新 UI 状态为处理中
    _updateState(CapsuleStateData.processing());

    // 2. 停止录音，获取最终文本 (AC3)
    final finalText = await _pipeline!.stop();

    // ignore: avoid_print
    print('[HotkeyController] 📝 最终文本: "$finalText"');

    // 3. 先隐藏窗口 (Wayland 焦点修复)
    // 在 Wayland 下，必须先隐藏窗口让原应用恢复焦点，
    // 否则 Fcitx5 的 commitString 无法生效
    await WindowService.instance.hide();

    // 4. 等待焦点恢复 (关键！)
    await Future.delayed(const Duration(milliseconds: 100));

    // 5. 提交文本到 Fcitx5 (AC4)
    await _submitText(finalText);

    // 6. 重置状态
    _state = HotkeyState.idle;
    _updateState(CapsuleStateData.idle());
  }

  /// 提交文本到 Fcitx5
  /// Story 3-7: 增强错误处理，保护提交失败的文本 (AC15)
  Future<void> _submitText(String text) async {
    if (text.isEmpty) return;

    try {
      await _fcitxClient!.sendText(text);
      _lastRecognizedText = null; // 成功后清空
      // ignore: avoid_print
      print('[HotkeyController] ✅ 文本已提交');
    } on FcitxError catch (e) {
      // Story 3-7: 保存文本，使用 FcitxError 细化消息
      _lastRecognizedText = text;
      // ignore: avoid_print
      print('[HotkeyController] ❌ 文本提交失败 (FcitxError): $e');
      _updateState(CapsuleStateData.error(
        CapsuleErrorType.socketError,
        fcitxError: e,
        preservedText: text,
      ));
      // 更新托盘图标为警告状态
      TrayService.instance.updateStatus(TrayStatus.warning);
      // 不自动隐藏，等待用户操作 (AC15)
      _state = HotkeyState.idle; // 允许用户重新触发
    } catch (e) {
      // 其他异常
      _lastRecognizedText = text;
      // ignore: avoid_print
      print('[HotkeyController] ❌ 文本提交失败: $e');
      _updateState(CapsuleStateData.error(
        CapsuleErrorType.socketError,
        preservedText: text,
      ));
      // 更新托盘图标为警告状态
      TrayService.instance.updateStatus(TrayStatus.warning);
      _state = HotkeyState.idle;
    }
  }

  /// VAD 端点事件处理 (自动提交)
  /// Story 3-7: 增强设备丢失处理 (AC13)
  void _onEndpoint(EndpointEvent event) {
    // ignore: avoid_print
    print('[HotkeyController] 🔔 VAD 端点: isVad=${event.isVadTriggered}, '
        'text="${event.finalText}", duration=${event.durationMs}ms, '
        'deviceLost=${event.isDeviceLost}');

    // Story 3-7 AC13: 设备断开时保存文本并显示警告
    if (event.isDeviceLost) {
      _handleDeviceLost(event.finalText);
      return;
    }

    if (event.isVadTriggered && _state == HotkeyState.recording) {
      // VAD 自动触发，执行提交流程
      _submitFromVad(event.finalText);
    }
  }

  /// Story 3-7: 处理设备丢失 (AC13)
  /// 保存已识别文本并显示警告，不自动隐藏窗口
  void _handleDeviceLost(String preservedText) {
    _lastRecognizedText = preservedText;
    _state = HotkeyState.idle; // 允许用户重新触发

    // 更新 UI 显示设备丢失错误
    _updateState(CapsuleStateData.error(
      CapsuleErrorType.audioDeviceLost,
      preservedText: preservedText.isNotEmpty ? preservedText : null,
    ));

    // 更新托盘图标为警告状态
    TrayService.instance.updateStatus(TrayStatus.warning);

    // ignore: avoid_print
    print('[HotkeyController] 🔌 设备丢失，已保存文本: "$preservedText"');
  }

  /// VAD 触发的提交 (无需再次 stop)
  Future<void> _submitFromVad(String finalText) async {
    _state = HotkeyState.submitting;

    // 1. 更新 UI 状态
    _updateState(CapsuleStateData.processing());

    // 2. 先隐藏窗口 (Wayland 焦点修复)
    await WindowService.instance.hide();

    // 3. 等待焦点恢复
    await Future.delayed(const Duration(milliseconds: 100));

    // 4. 提交文本
    await _submitText(finalText);

    // 5. 重置状态
    _state = HotkeyState.idle;
    _updateState(CapsuleStateData.idle());
  }

  /// 识别结果处理 (更新 UI 文本)
  void _onRecognitionResult(String text) {
    if (_state == HotkeyState.recording) {
      _updateState(CapsuleStateData.listening(text: text));
    }
  }

  /// 错误处理
  /// Story 3-7 AC9/AC10: 显示具体错误原因，提供可操作的恢复按钮
  /// Story 3-7: 处理录音错误
  /// Story 3-8: 移除硬编码错误消息，使用 CapsuleStateData.displayMessage 的国际化翻译
  void _handleError(PipelineError error) {
    final (errorType, errorMessage) = switch (error) {
      PipelineError.audioInitFailed => (
          CapsuleErrorType.audioInitFailed,
          null, // 使用 LanguageService 国际化
        ),
      PipelineError.deviceUnavailable => (
          CapsuleErrorType.audioNoDevice,
          null, // 使用 LanguageService 国际化
        ),
      PipelineError.modelNotReady => (
          CapsuleErrorType.modelNotFound,
          null, // 使用 LanguageService 国际化
        ),
      PipelineError.recognizerFailed => _getDetailedASRError(),
      PipelineError.none => (null, null),
    };

    if (errorType != null) {
      // Story 3-7 AC10: 错误状态保持显示，等待用户操作
      // 设置为 idle 状态允许用户重新触发快捷键或点击操作按钮
      _state = HotkeyState.idle;
      _updateState(CapsuleStateData.error(errorType, message: errorMessage));
      // 更新托盘图标为错误状态
      TrayService.instance.updateStatus(TrayStatus.error);
      // 不自动隐藏，由用户通过 dismissError() 或操作按钮关闭
    } else {
      // 无错误类型时直接重置
      _state = HotkeyState.idle;
    }
  }

  /// Story 3-7: 获取详细的 ASR 错误信息 (AC9)
  /// Story 3-8: 移除硬编码消息，使用 CapsuleStateData.displayMessage 的国际化翻译
  /// Story 2-7: 重构为使用 ASRError (ASR 引擎抽象层统一错误类型)
  (CapsuleErrorType, String?) _getDetailedASRError() {
    final asrError = _pipeline?.lastASRError ?? ASRError.none;

    return switch (asrError) {
      ASRError.libraryLoadFailed => (
          CapsuleErrorType.modelLoadFailed,
          null, // 使用 LanguageService 国际化
        ),
      ASRError.modelNotFound => (
          CapsuleErrorType.modelNotFound,
          null, // 使用 LanguageService 国际化
        ),
      ASRError.modelFileMissing => (
          CapsuleErrorType.modelIncomplete,
          null, // 使用 LanguageService 国际化
        ),
      ASRError.recognizerCreateFailed => (
          CapsuleErrorType.modelLoadFailed,
          null, // 使用 LanguageService 国际化
        ),
      ASRError.streamCreateFailed => (
          CapsuleErrorType.modelLoadFailed,
          null, // 使用 LanguageService 国际化
        ),
      ASRError.notInitialized => (
          CapsuleErrorType.modelLoadFailed,
          null, // 使用 LanguageService 国际化
        ),
      ASRError.vadInitFailed => (
          CapsuleErrorType.modelIncomplete, // VAD 模型缺失，需要下载
          null, // 使用 LanguageService 国际化
        ),
      ASRError.invalidConfig => (
          CapsuleErrorType.modelLoadFailed,
          null, // 使用 LanguageService 国际化
        ),
      ASRError.none => (
          CapsuleErrorType.modelLoadFailed,
          null, // 使用 LanguageService 国际化
        ),
    };
  }

  /// 更新 UI 状态
  void _updateState(CapsuleStateData stateData) {
    if (_stateController != null && !_stateController!.isClosed) {
      _stateController!.add(stateData);
    }
  }

  /// 释放资源
  Future<void> dispose() async {
    await _endpointSubscription?.cancel();
    await _resultSubscription?.cancel();
    HotkeyService.instance.onHotkeyPressed = null;
    _isInitialized = false;
    _state = HotkeyState.idle;
  }
}
