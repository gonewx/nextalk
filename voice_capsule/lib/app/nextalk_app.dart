import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../constants/settings_constants.dart';
import '../l10n/app_localizations.dart';
import '../services/audio_capture.dart';
import '../services/hotkey_controller.dart';
import '../services/language_service.dart';
import '../services/model_manager.dart';
import '../services/settings_service.dart';
import '../services/tray_service.dart';
import '../services/window_service.dart';
import '../state/capsule_state.dart';
import '../ui/audio_device_error_dialog.dart';
import '../ui/capsule_widget.dart';
import '../ui/error_action_widget.dart';
import '../ui/init_wizard/init_wizard.dart';

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
  /// 是否需要显示初始化向导
  late bool _needsInit;

  /// 当前是否处于扩展窗口模式
  bool _isExpanded = false;

  /// 初始化向导的目标引擎类型 (从托盘菜单触发时设置)
  EngineType? _targetEngineType;

  @override
  void initState() {
    super.initState();
    // Story 3-7 AC1: 首次运行检测到模型缺失时显示初始化向导
    // 使用 hasAnyEngineReady 检查是否有任何引擎可用 (支持回退机制)
    _needsInit = !widget.modelManager.hasAnyEngineReady;

    // 注册托盘服务回调：当用户尝试切换到没有模型的引擎时显示初始化向导
    TrayService.instance.onShowInitWizard = (targetEngine) {
      _showInitWizard(targetEngine: targetEngine);
    };

    // Story 3-9 AC16: 启动时检测到音频设备错误，延迟显示错误对话框
    if (widget.audioDeviceError != null &&
        widget.audioDeviceError != AudioCaptureError.none) {
      // 延迟显示对话框，确保 MaterialApp 已完全构建
      WidgetsBinding.instance.addPostFrameCallback((_) {
        _showAudioDeviceErrorDialog();
      });
    }
  }

  @override
  void dispose() {
    // 清理回调
    TrayService.instance.onShowInitWizard = null;
    super.dispose();
  }

  /// 初始化向导完成回调
  void _onInitCompleted() {
    // 重置窗口尺寸为正常胶囊尺寸并隐藏
    WindowService.instance.resetToNormalSize();
    WindowService.instance.hide();

    // 确定下载完成的引擎类型
    final downloadedEngine = _targetEngineType ?? SettingsService.instance.engineType;

    // 先更新状态，避免异步操作后 widget 已销毁
    setState(() {
      _needsInit = false;
      _targetEngineType = null; // 清除目标引擎
    });

    // ignore: avoid_print
    print('[NextalkApp] 初始化完成，窗口已隐藏，等待快捷键唤醒');

    // 异步触发引擎重新初始化（会更新 SettingsService.actualEngineType 并重建托盘菜单）
    _reinitializeEngineIfNeeded(downloadedEngine);
  }

  /// 异步重新初始化引擎（初始化向导完成后调用）
  Future<void> _reinitializeEngineIfNeeded(EngineType downloadedEngine) async {
    // 如果下载的引擎与当前配置不同，需要切换引擎
    // 这会触发 onEngineSwitch 回调，重新初始化 ASR 引擎
    if (downloadedEngine != SettingsService.instance.engineType) {
      // ignore: avoid_print
      print('[NextalkApp] 切换引擎配置: ${SettingsService.instance.engineType} -> $downloadedEngine');
      await SettingsService.instance.switchEngineType(downloadedEngine);
    } else {
      // 引擎类型相同，但可能是首次下载或重新下载，仍需触发引擎重新初始化
      // 直接调用 onEngineSwitch 回调（如果已注入）
      if (SettingsService.instance.onEngineSwitch != null) {
        // ignore: avoid_print
        print('[NextalkApp] 触发引擎重新初始化: $downloadedEngine');
        await SettingsService.instance.onEngineSwitch!(downloadedEngine);
      }
    }
  }

  /// 重新显示初始化向导（用于模型缺失时重新下载）
  /// [targetEngine] 目标引擎类型，从托盘菜单触发时传入
  void _showInitWizard({EngineType? targetEngine}) {
    setState(() {
      _needsInit = true;
      _targetEngineType = targetEngine;
    });
    // 设置初始化向导窗口大小并显示
    WindowService.instance.setInitWizardSize();
    WindowService.instance.show();

    // ignore: avoid_print
    print('[NextalkApp] 重新显示初始化向导, 目标引擎: $targetEngine');
  }

  /// Story 3-9 AC16: 显示音频设备错误对话框
  void _showAudioDeviceErrorDialog() {
    if (!mounted) return;

    final lang = LanguageService.instance;
    final deviceName = widget.audioDeviceName ?? 'default';

    // 根据错误类型生成错误原因描述
    final errorReason = _getAudioErrorReason(widget.audioDeviceError!, lang);

    // 显示窗口 (对话框需要可见的窗口)
    WindowService.instance.show();

    // 显示错误对话框
    showDialog(
      context: context,
      barrierDismissible: true,
      builder: (_) => AudioDeviceErrorDialog(
        deviceName: deviceName,
        errorReason: errorReason,
        onDismiss: () {
          // 对话框关闭后隐藏窗口
          WindowService.instance.hide();
        },
      ),
    );
  }

  /// Story 3-9: 根据错误类型获取本地化的错误原因描述
  String _getAudioErrorReason(AudioCaptureError error, LanguageService lang) {
    return switch (error) {
      AudioCaptureError.initializationFailed => lang.isZh
          ? 'PortAudio 初始化失败'
          : 'PortAudio initialization failed',
      AudioCaptureError.noInputDevice => lang.isZh
          ? '未检测到音频输入设备'
          : 'No audio input device detected',
      AudioCaptureError.deviceUnavailable => lang.isZh
          ? '设备不可用'
          : 'Device unavailable',
      AudioCaptureError.streamOpenFailed => lang.isZh
          ? '无法打开音频流 (设备可能被其他应用占用)'
          : 'Failed to open audio stream (device may be in use by another app)',
      AudioCaptureError.streamStartFailed => lang.isZh
          ? '无法启动音频流'
          : 'Failed to start audio stream',
      AudioCaptureError.readFailed => lang.isZh
          ? '音频读取失败'
          : 'Audio read failed',
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
            scaffoldBackgroundColor: Colors.transparent,
          ),
          home: Scaffold(
            backgroundColor: Colors.transparent,
            // Story 3-7: 根据初始化状态路由 UI
            body: _needsInit ? _buildInitWizard() : _buildCapsuleUI(),
          ),
        );
      },
    );
  }

  /// 构建初始化向导 (AC1-AC7)
  Widget _buildInitWizard() {
    return InitWizard(
      modelManager: widget.modelManager,
      onCompleted: _onInitCompleted,
      targetEngineType: _targetEngineType,
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
            : (l10n?.listening ?? '正在聆听...');

        // Story 3-7: 错误状态时显示操作按钮
        final isErrorWithActions = state.state == CapsuleState.error &&
            _shouldShowErrorActions(state.errorType);

        // SCP-002: 剪贴板复制成功状态（复制完成后才显示）
        final isCopiedToClipboard = state.state == CapsuleState.copiedToClipboard;

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
