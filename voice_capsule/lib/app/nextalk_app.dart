import 'dart:async';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:window_manager/window_manager.dart';

import '../constants/settings_constants.dart';
import '../l10n/app_localizations.dart';
import '../services/audio_capture.dart';
import '../services/hotkey_controller.dart';
import '../services/language_service.dart';
import '../services/model_manager.dart';
import '../services/settings_service.dart';
import '../services/tray_service.dart';
import '../services/update_service.dart';
import '../services/window_service.dart';
import '../state/capsule_state.dart';
import '../ui/capsule_widget.dart';
import '../ui/settings/settings_window.dart';
import '../ui/error_action_widget.dart';

/// Nextalk 应用根组件
/// Story 3-6: 完整业务流串联
/// Story 3-7: 错误状态操作按钮集成 + 初始化向导路由
/// Story 3-9: 启动时音频设备错误提示 (AC16, AC17)
///
/// 使用 StreamBuilder 绑定状态流到 UI，自动处理生命周期。
/// 根据模型状态路由到初始化向导或正常胶囊 UI。
class NextalkApp extends StatefulWidget {
  const NextalkApp({
    super.key,
    required this.stateController,
    required this.modelManager,
    this.audioDeviceError,
    this.audioDeviceName,
    this.audioErrorDetail,
  });

  /// 状态控制器 (由 main.dart 注入)
  final StreamController<CapsuleStateData> stateController;

  /// 模型管理器 (由 main.dart 注入)
  final ModelManager modelManager;

  /// Story 3-9: 音频设备错误 (AC16)
  final AudioCaptureError? audioDeviceError;

  /// Story 3-9: 配置的音频设备名称 (AC16)
  final String? audioDeviceName;

  /// Story 3-9: 详细错误信息 (AC16)
  final String? audioErrorDetail;

  @override
  State<NextalkApp> createState() => _NextalkAppState();
}

class _NextalkAppState extends State<NextalkApp> {
  bool _isExpanded = false;
  bool _settingsOpen = false;
  bool _settingsBusy = false;
  bool _recordingHint = false;
  int _recordingHintRevision = 0;
  bool _presentingRecordingHint = false;
  bool _initialGeneral = false;
  bool _windowTransition = false;
  EngineType? _initialEngine;
  int _settingsGeneration = 0;
  Timer? _updateNoticeTimer;
  String? _notifiedVersion;
  String? _trayUpdateVersion;

  void _onUpdateChanged() {
    final updater = UpdateService.instance;
    final release = updater.release;
    final trayVersion =
        '${release?.version}:${updater.phase == UpdatePhase.installed}';
    if (_trayUpdateVersion != trayVersion) {
      _trayUpdateVersion = trayVersion;
      unawaited(TrayService.instance.rebuildMenu());
    }
    if (release == null ||
        release.version == _notifiedVersion ||
        updater.phase != UpdatePhase.available) {
      _updateNoticeTimer?.cancel();
      _updateNoticeTimer = null;
      return;
    }
    _updateNoticeTimer ??=
        Timer.periodic(const Duration(seconds: 5), (_) async {
      if (!mounted ||
          HotkeyController.instance.state != HotkeyState.idle ||
          _windowTransition) {
        return;
      }
      _updateNoticeTimer?.cancel();
      _updateNoticeTimer = null;
      _notifiedVersion = release.version;
      final zh = LanguageService.instance.isZh;
      try {
        // 不抢焦点；系统通知不可用时仍保留托盘和设置页提示。
        await Process.run('notify-send', [
          '--app-name=Nextalk',
          'Nextalk',
          zh
              ? '发现新版本 ${release.version}，请打开设置查看并升级。'
              : 'Version ${release.version} is available. Open Settings to update.'
        ]);
      } catch (_) {/* 桌面可能未安装 libnotify */}
    });
  }

  @override
  void initState() {
    super.initState();
    UpdateService.instance.addListener(_onUpdateChanged);
    TrayService.instance.onShowModelSelection = () => _openSettings();
    TrayService.instance.onShowSettings = () => _openSettings(general: true);
    TrayService.instance.onShowDeepSeekSettings =
        () => _openSettings(engine: EngineType.deepseek);
    TrayService.instance.onShowInitWizard =
        (engine) => _showInitWizard(targetEngine: engine);
    WindowService.instance.onConfigurationClose = _closeSettings;
    HotkeyController.instance.onRecordingBlocked = _explainRecordingBlocked;
    final settings = SettingsService.instance;
    if (!widget.modelManager.isEngineReady(settings.engineType) ||
        (widget.audioDeviceError != null &&
            widget.audioDeviceError != AudioCaptureError.none)) {
      WidgetsBinding.instance.addPostFrameCallback((_) => _openSettings());
    }
  }

  @override
  void dispose() {
    UpdateService.instance.removeListener(_onUpdateChanged);
    _updateNoticeTimer?.cancel();
    TrayService.instance.onShowModelSelection = null;
    TrayService.instance.onShowSettings = null;
    TrayService.instance.onShowInitWizard = null;
    TrayService.instance.onShowDeepSeekSettings = null;
    WindowService.instance.onConfigurationClose = null;
    HotkeyController.instance.configurationOpen = false;
    HotkeyController.instance.onRecordingBlocked = null;
    super.dispose();
  }

  Future<void> _explainRecordingBlocked() async {
    if (!mounted || !_settingsOpen) return;
    setState(() {
      _recordingHint = true;
      _recordingHintRevision++;
    });
    if (_windowTransition || _presentingRecordingHint) return;
    _presentingRecordingHint = true;
    try {
      // 保留当前页面及未保存草稿，重复快捷键只更新同一条提示。
      await _prepareHiddenFrame();
      await WindowService.instance.presentConfigurationAttention();
    } finally {
      _presentingRecordingHint = false;
    }
  }

  Future<void> _openSettings({EngineType? engine, bool general = false}) async {
    if (!mounted || _windowTransition) return;
    if (_settingsOpen) {
      if (!_settingsBusy) {
        setState(() {
          _initialEngine = engine;
          _initialGeneral = general;
          _settingsGeneration++;
        });
        await _prepareHiddenFrame();
      }
      await WindowService.instance.show();
      await windowManager.focus();
      return;
    }
    if (HotkeyController.instance.state != HotkeyState.idle) return;
    _windowTransition = true;
    HotkeyController.instance.configurationOpen = true;
    final window = WindowService.instance;
    window.preventAutoHide = true;
    try {
      await window.hide();
      await window.setConfigurationMode(true);
      if (!mounted) return;
      setState(() {
        _settingsOpen = true;
        _recordingHint = false;
        _initialEngine = engine;
        _initialGeneral = general;
        _settingsGeneration++;
      });
      // 内容和最终几何均准备好后只映射一次窗口。
      await _prepareHiddenFrame();
      await window.show();
    } finally {
      _windowTransition = false;
    }
  }

  /// 隐藏窗口没有正常 vsync，不能直接等待 endOfFrame。
  /// Warm-up frame 不依赖窗口映射，先完成布局再显示，避免死锁和旧内容闪现。
  Future<void> _prepareHiddenFrame() async {
    final binding = WidgetsBinding.instance;
    final frame = binding.endOfFrame;
    binding.scheduleWarmUpFrame();
    await frame;
  }

  Future<void> _closeSettings() async {
    if (!mounted || _windowTransition || _settingsBusy) return;
    _windowTransition = true;
    final window = WindowService.instance;
    try {
      await window.hide();
      await windowManager.unmaximize();
      await window.setConfigurationMode(false);
      await window.resetToNormalSize();
      if (mounted) {
        setState(() {
          _settingsOpen = false;
          _isExpanded = false;
        });
      }
      await _prepareHiddenFrame();
      window.preventAutoHide = false;
      HotkeyController.instance.configurationOpen = false;
    } finally {
      _windowTransition = false;
    }
  }

  void _showInitWizard({EngineType? targetEngine}) {
    _openSettings(engine: targetEngine);
  }

  /// Story 3-9: 根据错误类型获取本地化的错误原因描述
  String _getAudioErrorReason(AudioCaptureError error, LanguageService lang) {
    return switch (error) {
      AudioCaptureError.initializationFailed =>
        lang.isZh ? 'PortAudio 初始化失败' : 'PortAudio initialization failed',
      AudioCaptureError.noInputDevice =>
        lang.isZh ? '未检测到音频输入设备' : 'No audio input device detected',
      AudioCaptureError.deviceUnavailable =>
        lang.isZh ? '设备不可用' : 'Device unavailable',
      AudioCaptureError.streamOpenFailed => lang.isZh
          ? '无法打开音频流 (设备可能被其他应用占用)'
          : 'Failed to open audio stream (device may be in use by another app)',
      AudioCaptureError.streamStartFailed =>
        lang.isZh ? '无法启动音频流' : 'Failed to start audio stream',
      AudioCaptureError.readFailed =>
        lang.isZh ? '音频读取失败' : 'Audio read failed',
      AudioCaptureError.none => '',
    };
  }

  @override
  Widget build(BuildContext context) {
    // Story 3-8: 使用 ValueListenableBuilder 响应 Locale 变化 (Task 5.1)
    return ValueListenableBuilder<Locale>(
      valueListenable: LanguageService.instance.localeNotifier,
      builder: (context, locale, _) {
        return MaterialApp(
          debugShowCheckedModeBanner: false,
          title: 'Nextalk Voice Capsule',
          // Story 3-8: 国际化配置
          locale: locale,
          localizationsDelegates: AppLocalizations.localizationsDelegates,
          supportedLocales: AppLocalizations.supportedLocales,
          theme: ThemeData.dark().copyWith(
            colorScheme: ColorScheme.fromSeed(
                seedColor: const Color(0xFFEF5350),
                brightness: Brightness.dark),
            scaffoldBackgroundColor: Colors.transparent,
          ),
          home: Scaffold(
            backgroundColor:
                _settingsOpen ? const Color(0xFF1A1A1A) : Colors.transparent,
            // Story 3-7: 根据初始化状态路由 UI
            body: _settingsOpen
                ? SettingsWindow(
                    key: ValueKey(_settingsGeneration),
                    modelManager: widget.modelManager,
                    initialEngine: _initialEngine,
                    initialGeneral: _initialGeneral,
                    onBusyChanged: (busy) => _settingsBusy = busy,
                    recordingRequested: _recordingHint,
                    recordingHintRevision: _recordingHintRevision,
                    onDismissRecordingHint: () =>
                        setState(() => _recordingHint = false),
                    notice: widget.audioDeviceError != null &&
                            widget.audioDeviceError != AudioCaptureError.none
                        ? _getAudioErrorReason(
                            widget.audioDeviceError!, LanguageService.instance)
                        : null,
                    onClose: _closeSettings)
                : _buildCapsuleUI(),
          ),
        );
      },
    );
  }

  /// 构建正常的胶囊 UI
  Widget _buildCapsuleUI() {
    return StreamBuilder<CapsuleStateData>(
      stream: widget.stateController.stream,
      // 初始状态使用 listening，便于开发调试
      // 生产环境中窗口启动时隐藏，首次显示时 HotkeyController 会发送 listening 状态
      initialData: CapsuleStateData.listening(),
      builder: (context, snapshot) {
        final state = snapshot.data ?? CapsuleStateData.listening();
        final l10n = AppLocalizations.of(context);

        // 状态相关的显示逻辑由 CapsuleWidget 统一处理
        // NextalkApp 只负责传递状态和控制 showHint
        final showHint = state.state == CapsuleState.listening &&
            state.recognizedText.isEmpty;

        // Story 3-8: 错误状态的提示文字 (国际化)
        final hintText = state.state == CapsuleState.error
            ? state.displayMessage
            : SettingsService.instance.actualEngineType == EngineType.deepseek
                ? (LanguageService.instance.isZh
                    ? '正在录音（最长 120 秒）'
                    : 'Recording (up to 120 seconds)')
                : (l10n?.listening ?? '正在聆听...');

        // Story 3-7: 错误状态时显示操作按钮
        final isErrorWithActions = state.state == CapsuleState.error &&
            _shouldShowErrorActions(state.errorType);

        // SCP-002: 剪贴板复制成功状态（复制完成后才显示）
        final isCopiedToClipboard =
            state.state == CapsuleState.copiedToClipboard;

        // 动态调整窗口大小：错误状态需要更多空间
        _updateWindowSize(isErrorWithActions);

        // 使用 LayoutBuilder 检测可用空间，避免在窗口扩展前渲染导致溢出警告
        return LayoutBuilder(
          builder: (context, constraints) {
            // 只有当窗口高度足够时才显示操作按钮 (阈值 > 基础高度)
            final hasEnoughSpace = constraints.maxHeight > 140;
            final showActions = isErrorWithActions && hasEnoughSpace;

            return Column(
              mainAxisAlignment: MainAxisAlignment.center,
              mainAxisSize: MainAxisSize.min,
              children: [
                CapsuleWidget(
                  text: state.recognizedText,
                  showHint: showHint,
                  hintText: hintText,
                  stateData: state,
                ),
                // SCP-002: 剪贴板复制成功提示（醒目样式）
                if (isCopiedToClipboard)
                  Padding(
                    padding: const EdgeInsets.only(top: 10),
                    child: Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 12,
                        vertical: 6,
                      ),
                      decoration: BoxDecoration(
                        color: const Color(0xCC000000), // 80% 黑色背景
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(
                          color: const Color(0xFF4CAF50), // 绿色边框
                          width: 1,
                        ),
                      ),
                      child: Text(
                        LanguageService.instance.tr('clipboard_paste_hint'),
                        style: const TextStyle(
                          fontSize: 13,
                          color: Color(0xFF81C784), // 浅绿色文字
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                    ),
                  ),
                // Story 3-7: 错误操作按钮 (只在空间足够时显示)
                if (showActions)
                  Padding(
                    padding: const EdgeInsets.only(top: 12),
                    child: _buildErrorActions(context, state),
                  ),
              ],
            );
          },
        );
      },
    );
  }

  /// 根据是否需要扩展模式动态调整窗口大小
  void _updateWindowSize(bool needsExpanded) {
    if (needsExpanded != _isExpanded) {
      _isExpanded = needsExpanded;
      // 使用 post-frame callback 确保在布局完成后调整窗口
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (!mounted || _settingsOpen || _windowTransition) return;
        WindowService.instance.setExpandedMode(needsExpanded);
        // 当显示错误操作按钮时，阻止快捷键自动隐藏窗口
        WindowService.instance.preventAutoHide = needsExpanded;
      });
    }
  }

  /// 判断是否应该显示错误操作按钮
  /// Story 3-7 AC10: 错误状态下提供可操作的恢复按钮
  bool _shouldShowErrorActions(CapsuleErrorType? errorType) {
    if (errorType == null) return false;
    return switch (errorType) {
      // 音频相关
      CapsuleErrorType.audioNoDevice => true,
      CapsuleErrorType.audioDeviceBusy => true,
      CapsuleErrorType.audioDeviceLost => true,
      CapsuleErrorType.audioInitFailed => true,
      // 模型相关 (AC8-AC10)
      CapsuleErrorType.modelNotFound => true,
      CapsuleErrorType.modelIncomplete => true,
      CapsuleErrorType.modelCorrupted => true,
      CapsuleErrorType.modelLoadFailed => true,
      // Socket 相关
      CapsuleErrorType.socketError => true,
      _ => false,
    };
  }

  /// 根据错误类型构建操作按钮
  Widget _buildErrorActions(BuildContext context, CapsuleStateData state) {
    final actions = _getActionsForError(context, state);

    return ErrorActionWidget(
      errorType: state.errorType!,
      message: '', // 消息已在 CapsuleWidget 中显示
      actions: actions,
      preservedText: state.preservedText,
    );
  }

  /// 根据错误类型获取操作按钮列表
  /// Story 3-7: AC8-AC10 模型错误操作按钮
  /// Story 3-8: 按钮标签国际化
  List<ErrorAction> _getActionsForError(
      BuildContext context, CapsuleStateData state) {
    final errorType = state.errorType;
    if (errorType == null) return [];
    final l10n = AppLocalizations.of(context);

    switch (errorType) {
      // 音频设备错误
      case CapsuleErrorType.audioNoDevice:
      case CapsuleErrorType.audioDeviceBusy:
      case CapsuleErrorType.audioInitFailed:
        return [
          ErrorAction(
            label: l10n?.actionRefresh ?? '刷新检测',
            onPressed: () => HotkeyController.instance.retryRecording(),
            isPrimary: true,
          ),
        ];

      // 设备丢失 (可能有保护的文本)
      case CapsuleErrorType.audioDeviceLost:
        final hasPreservedText = state.preservedText?.isNotEmpty ?? false;
        return [
          if (hasPreservedText)
            ErrorAction(
              label: l10n?.actionCopyText ?? '复制文本',
              onPressed: () =>
                  _copyPreservedText(context, state.preservedText!),
            ),
          ErrorAction(
            label: l10n?.actionClose ?? '关闭',
            onPressed: () => HotkeyController.instance.dismissError(),
            isPrimary: !hasPreservedText,
          ),
        ];

      // Socket 错误 (可能有保护的文本)
      case CapsuleErrorType.socketError:
        final hasPreservedText = state.preservedText?.isNotEmpty ?? false;
        return [
          if (hasPreservedText) ...[
            ErrorAction(
              label: l10n?.actionCopyText ?? '复制文本',
              onPressed: () =>
                  _copyPreservedText(context, state.preservedText!),
            ),
            ErrorAction(
              label: l10n?.actionRetrySubmit ?? '重试提交',
              onPressed: () => HotkeyController.instance.retrySubmit(),
              isPrimary: true,
            ),
            ErrorAction(
              label: l10n?.actionDiscard ?? '放弃',
              onPressed: () => HotkeyController.instance.discardPreservedText(),
            ),
          ] else
            ErrorAction(
              label: l10n?.actionClose ?? '关闭',
              onPressed: () => HotkeyController.instance.dismissError(),
              isPrimary: true,
            ),
        ];

      // 模型错误 (AC8-AC10)
      case CapsuleErrorType.modelNotFound:
      case CapsuleErrorType.modelIncomplete:
        return [
          ErrorAction(
            label: l10n?.actionRedownload ?? '重新下载',
            onPressed: () {
              // 直接显示初始化向导，不需要先隐藏窗口
              // 恢复托盘状态
              TrayService.instance.updateStatus(TrayStatus.normal);
              // 使用当前配置的引擎类型
              final currentEngine = SettingsService.instance.engineType;
              _showInitWizard(targetEngine: currentEngine);
            },
            isPrimary: true,
          ),
          ErrorAction(
            label: l10n?.actionClose ?? '关闭',
            onPressed: () => HotkeyController.instance.dismissError(),
          ),
        ];

      // 模型损坏 (AC8: 删除并重新下载)
      case CapsuleErrorType.modelCorrupted:
        return [
          ErrorAction(
            label: l10n?.actionDeleteAndRedownload ?? '删除并重新下载',
            onPressed: () async {
              await widget.modelManager.deleteModel();
              // 直接显示初始化向导
              TrayService.instance.updateStatus(TrayStatus.normal);
              // 使用当前配置的引擎类型
              final currentEngine = SettingsService.instance.engineType;
              _showInitWizard(targetEngine: currentEngine);
            },
            isPrimary: true,
          ),
          ErrorAction(
            label: l10n?.actionClose ?? '关闭',
            onPressed: () => HotkeyController.instance.dismissError(),
          ),
        ];

      // 模型加载失败 (AC9: 显示具体原因)
      case CapsuleErrorType.modelLoadFailed:
        return [
          ErrorAction(
            label: l10n?.actionRedownload ?? '重新下载',
            onPressed: () {
              TrayService.instance.updateStatus(TrayStatus.normal);
              // 使用当前配置的引擎类型
              final currentEngine = SettingsService.instance.engineType;
              _showInitWizard(targetEngine: currentEngine);
            },
            isPrimary: true,
          ),
          ErrorAction(
            label: l10n?.actionRetry ?? '重试',
            onPressed: () => HotkeyController.instance.retryRecording(),
          ),
          ErrorAction(
            label: l10n?.actionClose ?? '关闭',
            onPressed: () => HotkeyController.instance.dismissError(),
          ),
        ];

      default:
        return [
          ErrorAction(
            label: l10n?.actionClose ?? '关闭',
            onPressed: () => HotkeyController.instance.dismissError(),
            isPrimary: true,
          ),
        ];
    }
  }

  /// 复制保护的文本到剪贴板
  /// Story 3-8: 使用国际化的 SnackBar 提示
  Future<void> _copyPreservedText(BuildContext context, String text) async {
    await Clipboard.setData(ClipboardData(text: text));
    if (context.mounted) {
      final l10n = AppLocalizations.of(context);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(l10n?.notifyTextCopied ?? '文本已复制到剪贴板'),
          duration: const Duration(seconds: 2),
        ),
      );
    }
  }
}
