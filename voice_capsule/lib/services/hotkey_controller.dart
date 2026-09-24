import 'dart:async';

import 'package:flutter/services.dart';

import 'asr/asr_engine.dart';
import 'audio_inference_pipeline.dart';
import 'cancel_key_service.dart';
import 'settings_service.dart';
import 'tray_service.dart';
import 'window_service.dart';
import 'fcitx_client.dart';
import 'gnome_inject_client.dart';
import 'hotkey_service.dart';
import '../state/capsule_state.dart';

/// 快捷键控制器状态
enum HotkeyState {
  idle, // 空闲 (窗口隐藏)
  recording, // 录音中 (窗口显示，红灯呼吸)
  submitting, // 提交中 (处理文本上屏)
}

/// 注入后端（三级注入链决策结果）
enum InjectBackend {
  fcitx, // fcitx5 socket 直接上屏
  gnome, // GNOME Shell 扩展 D-Bus 上屏 (Fedora/ibus 等无 fcitx5 环境)
  clipboard, // 剪贴板 fallback
}

/// 三级注入链决策：fcitx5 socket → GNOME 扩展 → 剪贴板
///
/// 纯逻辑函数，供单测覆盖 spec I/O 矩阵。探测按需短路：
/// - fcitx5 可用时不探测 GNOME（Debian 路径零回归）
/// - 空文本不探测 GNOME（不调用注入后端，走剪贴板路径直接收尾）
///
/// 注：剪贴板模式的组合语义（"任一直接注入后端可用即非剪贴板模式"）
/// 在此层体现；FcitxClient.isClipboardMode 保持只反映 fcitx5 自身状态。
Future<InjectBackend> decideInjectBackend({
  required String text,
  required Future<bool> Function() fcitxAvailable,
  required Future<bool> Function() gnomeAvailable,
}) async {
  if (await fcitxAvailable()) return InjectBackend.fcitx;
  if (text.isEmpty) return InjectBackend.clipboard;
  if (await gnomeAvailable()) return InjectBackend.gnome;
  return InjectBackend.clipboard;
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
///   |                          | (VAD 触发 / Esc 取消)     | (Esc 取消)
///   └──────────────────────────┴──────────────────────────┘
/// ```
class HotkeyController {
  HotkeyController._();
  static final HotkeyController instance = HotkeyController._();

  // === 依赖服务 ===
  AudioInferencePipeline? _pipeline;
  FcitxClient? _fcitxClient;
  GnomeInjectClient? _gnomeClient;
  StreamController<CapsuleStateData>? _stateController;

  // === 状态管理 ===
  HotkeyState _state = HotkeyState.idle;
  StreamSubscription<EndpointEvent>? _endpointSubscription;
  StreamSubscription<String>? _resultSubscription;
  bool _isInitialized = false;
  bool _isProcessing = false; // 防止快速按键竞态条件
  DateTime? _lastHotkeyTime; // 防抖：记录上次按键时间
  static const _debounceMs = 300; // 防抖间隔（毫秒）

  /// 提交流程中断标志：用于支持用户快速重按时打断正在进行的提交
  bool _submitInterrupted = false;

  /// 提交流程取消标志：用户按 Esc 放弃本次输入 (与 _submitInterrupted 不同，
  /// 取消后文本直接丢弃，不保存、不上屏)
  bool _submitCancelled = false;

  /// 最近一次预览文本 (处理中状态继续显示，避免胶囊文字突然清空)
  String _lastPreviewText = '';

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
    // ignore: avoid_print
    print('[HotkeyController] show() 调用，当前状态: $_state');

    if (_state == HotkeyState.idle) {
      await _startRecording();
    } else if (_state == HotkeyState.submitting) {
      // 用户快速重按：打断正在进行的提交流程，优先开始新的录音
      // ignore: avoid_print
      print('[HotkeyController] 用户快速重按，打断提交流程');
      _submitInterrupted = true;
      // 立即开始新的录音（不等待 submitting 完成）
      await _startRecording();
    }
  }

  /// 隐藏窗口
  Future<void> hide() async {
    // ignore: avoid_print
    print('[HotkeyController] hide() 调用，当前状态: $_state');

    // 初始化向导模式下，不响应快捷键隐藏
    if (WindowService.instance.isInInitWizardMode) {
      // ignore: avoid_print
      print('[HotkeyController] 初始化向导模式，忽略 hide');
      return;
    }

    // 阻止自动隐藏模式下（如显示错误操作按钮时），不响应快捷键隐藏
    if (WindowService.instance.preventAutoHide) {
      // ignore: avoid_print
      print('[HotkeyController] preventAutoHide 模式，忽略 hide');
      return;
    }

    if (_state == HotkeyState.recording) {
      await _stopAndSubmit();
    } else if (_state == HotkeyState.submitting) {
      // 正在提交中，等待完成后隐藏
      // ignore: avoid_print
      print('[HotkeyController] 正在提交中，忽略 hide');
    } else {
      // idle 状态，直接隐藏窗口
      if (WindowService.instance.isVisible) {
        await WindowService.instance.hide();
        _updateState(CapsuleStateData.idle());
      }
    }
  }

  /// 取消当前语音输入 (Esc)
  ///
  /// - 录音中：立即隐藏胶囊、停止录音并丢弃识别结果，不上屏
  /// - 提交中：在上屏前拦截，丢弃文本
  /// - 空闲但胶囊仍显示 (错误提示/剪贴板提示)：关闭胶囊
  Future<void> cancel() async {
    // ignore: avoid_print
    print('[HotkeyController] cancel() 调用，当前状态: $_state');

    if (WindowService.instance.isInInitWizardMode) return;

    switch (_state) {
      case HotkeyState.recording:
        CancelKeyService.instance.disarm();
        // 先置为 submitting，挡住取消过程中到达的快捷键
        _state = HotkeyState.submitting;
        _lastPreviewText = '';
        // 先隐藏窗口给出即时反馈，再慢慢释放麦克风
        await WindowService.instance.hide();
        _updateState(CapsuleStateData.idle());
        await _pipeline?.cancel();
        // 取消期间用户可能已经开始了新的录音，不能覆盖它
        if (_state == HotkeyState.submitting) {
          _state = HotkeyState.idle;
        }
        TrayService.instance.updateStatus(TrayStatus.normal);
        // ignore: avoid_print
        print('[HotkeyController] 🚫 已取消本次录音');
        break;
      case HotkeyState.submitting:
        _submitCancelled = true;
        break;
      case HotkeyState.idle:
        if (WindowService.instance.isVisible) {
          await dismissError();
        }
        break;
    }
  }

  /// Story 3-7: 重试提交保存的文本 (AC15)
  /// SCP-002: 同样支持剪贴板模式
  Future<void> retrySubmit() async {
    if (_lastRecognizedText == null || _lastRecognizedText!.isEmpty) return;

    final text = _lastRecognizedText!;
    _state = HotkeyState.submitting;
    _submitInterrupted = false; // 重置中断标志 (GNOME 路径会检查此标志)
    _updateState(CapsuleStateData.processing());

    // 三级注入链决策：fcitx5 → GNOME 扩展 → 剪贴板
    final backend = await decideInjectBackend(
      text: text,
      fcitxAvailable: _fcitxClient!.isAvailable,
      gnomeAvailable: _gnomeClient!.isAvailable,
    );

    if (backend != InjectBackend.fcitx) {
      // GNOME 扩展或剪贴板模式
      await _submitViaGnomeOrClipboard(text, backend);
      TrayService.instance.updateStatus(TrayStatus.normal);
      return;
    }

    // Fcitx5 模式：先隐藏窗口
    await WindowService.instance.hide();
    await Future.delayed(const Duration(milliseconds: 100));

    await _submitTextToFcitx(text);

    // 如果提交成功，重置状态
    if (_lastRecognizedText == null) {
      _state = HotkeyState.idle;
      _updateState(CapsuleStateData.idle());
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
    GnomeInjectClient? gnomeInjectClient,
  }) async {
    if (_isInitialized) return;

    _pipeline = pipeline;
    _fcitxClient = fcitxClient;
    // GNOME 扩展注入后端（三级注入链第二级）；缺省内部创建，懒连接
    _gnomeClient = gnomeInjectClient ?? GnomeInjectClient();
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
    // 防止快速按键导致的竞态条件
    if (_isProcessing) {
      // ignore: avoid_print
      print('[HotkeyController] ⏳ 忽略按键，上一操作正在进行中');
      return;
    }

    _isProcessing = true;

    try {
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
    } finally {
      _isProcessing = false;
    }
  }

  /// 开始录音 (Idle -> Recording)
  ///
  /// AC1: 窗口瞬间出现
  /// AC2: 自动开始录音
  Future<void> _startRecording() async {
    _state = HotkeyState.recording;
    _submitCancelled = false;
    _lastPreviewText = '';

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

    // 启动期间已被取消 (如 nextalk --cancel)：立即释放麦克风
    if (_state != HotkeyState.recording) {
      await _pipeline!.cancel();
      return;
    }

    // 录音期间允许 Esc 取消 (由 Fcitx5 插件 / GNOME 扩展代为捕获)
    CancelKeyService.instance.arm();

    // ignore: avoid_print
    print('[HotkeyController] 🎤 开始录音');
  }

  /// 停止录音并提交 (Recording -> Submitting -> Idle)
  ///
  /// AC3: 立即停止录音
  /// AC4: 提交文本到活动窗口
  /// AC5: 提交后主窗口瞬间隐藏
  ///
  /// 注意：此方法支持被 show() 中断
  /// 如果用户在提交过程中快速重按，会设置 _submitInterrupted 标志，
  /// 此时会跳过文本提交，让新的录音流程接管。
  ///
  /// SCP-002: 剪贴板模式时保持窗口显示，复制完成后显示提示
  Future<void> _stopAndSubmit() async {
    _state = HotkeyState.submitting;
    _submitInterrupted = false; // 重置中断标志
    _submitCancelled = false;

    // 1. 更新 UI 状态为处理中 (保留已识别文本，避免胶囊文字突然清空)
    _updateState(CapsuleStateData.processing(text: _lastPreviewText));

    // 2. 停止录音，获取最终文本 (AC3)
    // 注意：pipeline.stop() 会等待所有处理中的数据完成
    final rawText = await _pipeline!.stop();
    final finalText = _postProcess(rawText);
    _lastPreviewText = '';

    // ignore: avoid_print
    print('[HotkeyController] 📝 最终文本: "$finalText" (原始: "$rawText")');

    // 用户在收尾期间按了 Esc：丢弃文本 (收尾期间 Esc 仍保持捕获)
    if (await _finishIfCancelled()) return;

    // 即将上屏，把 Esc 还给应用；若已被快速重按打断，新的录音仍需要它
    if (_state != HotkeyState.recording) {
      CancelKeyService.instance.disarm();
    }

    // 3. 检查是否被中断（用户快速重按）
    if (_submitInterrupted) {
      // ignore: avoid_print
      print('[HotkeyController] ⚡ 提交被中断，用户开始新的录音');
      // 不隐藏窗口，不提交文字，新的录音流程已经接管
      // 但要保存文字以防丢失（如果有内容的话）
      if (finalText.isNotEmpty) {
        _lastRecognizedText = finalText;
        // ignore: avoid_print
        print('[HotkeyController] 💾 已保存被中断的文本: "$finalText"');
      }
      return;
    }

    // 4. SCP-002: 三级注入链决策 (fcitx5 → GNOME 扩展 → 剪贴板)
    final backend = await decideInjectBackend(
      text: finalText,
      fcitxAvailable: _fcitxClient!.isAvailable,
      gnomeAvailable: _gnomeClient!.isAvailable,
    );

    if (backend != InjectBackend.fcitx) {
      // GNOME 扩展或剪贴板模式
      // ignore: avoid_print
      print('[HotkeyController] Fcitx5 不可用，注入后端: $backend');
      await _submitViaGnomeOrClipboard(finalText, backend);
      return;
    }

    // 5. Fcitx5 模式：先隐藏窗口 (Wayland 焦点修复)
    // 在 Wayland 下，必须先隐藏窗口让原应用恢复焦点，
    // 否则 Fcitx5 的 commitString 无法生效
    await WindowService.instance.hide();

    // 6. 等待焦点恢复 (关键！)
    await Future.delayed(const Duration(milliseconds: 100));

    // 7. 再次检查是否被中断（在等待焦点恢复期间可能被打断）
    if (await _finishIfCancelled()) return;
    if (_submitInterrupted) {
      // ignore: avoid_print
      print('[HotkeyController] ⚡ 提交在焦点等待期间被中断');
      if (finalText.isNotEmpty) {
        _lastRecognizedText = finalText;
      }
      return;
    }

    // 8. 提交文本到 Fcitx5 (AC4)
    await _submitTextToFcitx(finalText);

    // 9. 重置状态
    _state = HotkeyState.idle;
    _updateState(CapsuleStateData.idle());
  }

  /// GNOME 扩展或剪贴板提交 (fcitx5 不可用时的二级注入链)
  ///
  /// GNOME 路径复用 fcitx5 的"隐藏窗口 → 等待焦点恢复 → 中断检查"流程
  /// （焦点不在目标应用时 Main.inputMethod.commit 无效）；
  /// 任何失败恢复窗口并走剪贴板 fallback，保证文本不丢失。
  /// 剪贴板模式与现状一致：保持窗口显示，直接复制。
  Future<void> _submitViaGnomeOrClipboard(
    String text,
    InjectBackend backend,
  ) async {
    if (backend != InjectBackend.gnome) {
      // 剪贴板模式：保持窗口显示，直接复制（空文本在其内部直接收尾）
      await _copyToClipboardWithPrompt(text);
      return;
    }

    // GNOME 模式：先隐藏窗口，等待焦点恢复 (与 fcitx5 路径一致)
    await WindowService.instance.hide();
    await Future.delayed(const Duration(milliseconds: 100));

    // 焦点等待期间可能被用户快速重按打断或 Esc 取消
    if (await _finishIfCancelled()) return;
    if (_submitInterrupted) {
      // ignore: avoid_print
      print('[HotkeyController] ⚡ GNOME 提交在焦点等待期间被中断');
      if (text.isNotEmpty) {
        _lastRecognizedText = text;
      }
      return;
    }

    if (await _gnomeClient!.commitText(text)) {
      _lastRecognizedText = null; // 成功后清空
      // ignore: avoid_print
      print('[HotkeyController] ✅ 文本已通过 GNOME 扩展提交');
      _state = HotkeyState.idle;
      _updateState(CapsuleStateData.idle());
      return;
    }

    // 失败：恢复窗口，走剪贴板 fallback (文本不丢失)
    // ignore: avoid_print
    print('[HotkeyController] ❌ GNOME 扩展提交失败，降级剪贴板');
    await WindowService.instance.show();
    await _copyToClipboardWithPrompt(text);
  }

  /// 若用户在提交流程中按了 Esc，则丢弃文本并回到 idle，返回 true
  Future<bool> _finishIfCancelled() async {
    if (!_submitCancelled) return false;
    _submitCancelled = false;
    CancelKeyService.instance.disarm();
    // ignore: avoid_print
    print('[HotkeyController] 🚫 提交已被用户取消');
    await WindowService.instance.hide();
    _state = HotkeyState.idle;
    _updateState(CapsuleStateData.idle());
    return true;
  }

  /// 识别文本后处理 (自动纠错)，失败时退回原文，绝不丢字
  String _postProcess(String text) {
    try {
      return SettingsService.instance.textPostProcessor.process(text);
    } catch (e) {
      // ignore: avoid_print
      print('[HotkeyController] ⚠️ 文本后处理失败，使用原文: $e');
      return text;
    }
  }

  /// 提交文本到 Fcitx5 (仅用于 Fcitx5 可用时)
  /// Story 3-7: 增强错误处理，保护提交失败的文本 (AC15)
  Future<void> _submitTextToFcitx(String text) async {
    if (text.isEmpty) return;

    try {
      await _fcitxClient!.sendText(text);
      _lastRecognizedText = null; // 成功后清空
      // ignore: avoid_print
      print('[HotkeyController] ✅ 文本已提交');
    } on FcitxError catch (e) {
      // 连接失败时先尝试 GNOME 扩展，再降级剪贴板 (三级注入链)
      if (e == FcitxError.connectionFailed ||
          e == FcitxError.reconnectFailed ||
          e == FcitxError.socketNotFound) {
        // 此时窗口已隐藏、焦点已回到目标应用，可直接尝试 GNOME 提交
        if (await _gnomeClient!.isAvailable() &&
            await _gnomeClient!.commitText(text)) {
          _lastRecognizedText = null; // 成功后清空
          // ignore: avoid_print
          print('[HotkeyController] ✅ 文本已通过 GNOME 扩展提交 (fcitx5 fallback)');
          return;
        }
        // 重新显示窗口（已隐藏），使用剪贴板模式
        await WindowService.instance.show();
        await _copyToClipboardWithPrompt(text);
        return;
      }

      // 其他错误：保存文本，显示错误
      _lastRecognizedText = text;
      // ignore: avoid_print
      print('[HotkeyController] ❌ 文本提交失败 (FcitxError): $e');
      // 重新显示窗口显示错误
      await WindowService.instance.show();
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
      // 其他异常：重新显示窗口，使用剪贴板 fallback
      await WindowService.instance.show();
      await _copyToClipboardWithPrompt(text);
    }
  }

  /// SCP-002: 剪贴板模式 - 保持窗口显示，复制文本并显示提示
  /// 此方法在窗口**保持显示**的状态下调用，不需要重新显示窗口
  Future<void> _copyToClipboardWithPrompt(String text) async {
    if (text.isEmpty) {
      // 没有文本，直接隐藏窗口
      await WindowService.instance.hide();
      _state = HotkeyState.idle;
      _updateState(CapsuleStateData.idle());
      return;
    }

    try {
      await Clipboard.setData(ClipboardData(text: text));
      _lastRecognizedText = null; // 成功复制后清空

      // ignore: avoid_print
      print('[HotkeyController] 📋 文本已复制到剪贴板: "$text"');

      // 窗口保持显示，更新状态显示提示
      _state = HotkeyState.idle;
      _updateState(CapsuleStateData.copiedToClipboard(text: text));

      // 2秒后自动隐藏窗口
      Future.delayed(const Duration(seconds: 2), () {
        if (_state == HotkeyState.idle) {
          WindowService.instance.hide();
          _updateState(CapsuleStateData.idle());
        }
      });
    } catch (e) {
      // 剪贴板也失败，保存文本显示错误
      _lastRecognizedText = text;
      // ignore: avoid_print
      print('[HotkeyController] ❌ 复制到剪贴板失败: $e');
      _updateState(CapsuleStateData.error(
        CapsuleErrorType.socketError,
        preservedText: text,
      ));
      TrayService.instance.updateStatus(TrayStatus.warning);
      _state = HotkeyState.idle;
    }
  }

  /// VAD 端点事件处理
  /// PTT 模式：VAD 端点只作为视觉反馈，不触发自动提交
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

    // PTT 模式：VAD 端点不触发自动提交
    // 只在用户释放按键时（hide 命令）才提交
    // VAD 端点仅用于内部状态跟踪，不改变录音状态
  }

  /// Story 3-7: 处理设备丢失 (AC13)
  /// 保存已识别文本并显示警告，不自动隐藏窗口
  void _handleDeviceLost(String rawText) {
    CancelKeyService.instance.disarm();
    final preservedText = _postProcess(rawText);
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
  /// SCP-002: 同样支持剪贴板模式
  Future<void> _submitFromVad(String finalText) async {
    _state = HotkeyState.submitting;
    _submitInterrupted = false; // 重置中断标志 (GNOME 路径会检查此标志)

    // 1. 更新 UI 状态
    _updateState(CapsuleStateData.processing());

    // 2. 三级注入链决策 (fcitx5 → GNOME 扩展 → 剪贴板)
    final backend = await decideInjectBackend(
      text: finalText,
      fcitxAvailable: _fcitxClient!.isAvailable,
      gnomeAvailable: _gnomeClient!.isAvailable,
    );

    if (backend != InjectBackend.fcitx) {
      // GNOME 扩展或剪贴板模式
      await _submitViaGnomeOrClipboard(finalText, backend);
      return;
    }

    // 3. Fcitx5 模式：先隐藏窗口 (Wayland 焦点修复)
    await WindowService.instance.hide();

    // 4. 等待焦点恢复
    await Future.delayed(const Duration(milliseconds: 100));

    // 5. 提交文本
    await _submitTextToFcitx(finalText);

    // 6. 重置状态
    _state = HotkeyState.idle;
    _updateState(CapsuleStateData.idle());
  }

  /// 识别结果处理 (更新 UI 文本)
  void _onRecognitionResult(String text) {
    if (_state == HotkeyState.recording) {
      // 预览与上屏走同一个后处理器，所见即所得
      _lastPreviewText = _postProcess(text);
      _updateState(CapsuleStateData.listening(text: _lastPreviewText));
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

    CancelKeyService.instance.disarm();

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
    await _gnomeClient?.dispose();
    _gnomeClient = null;
    HotkeyService.instance.onHotkeyPressed = null;
    CancelKeyService.instance.disarm();
    _isInitialized = false;
    _isProcessing = false;
    _submitInterrupted = false;
    _submitCancelled = false;
    _state = HotkeyState.idle;
  }
}
