import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../services/hotkey_controller.dart';
import '../services/model_manager.dart';
import '../services/window_service.dart';
import '../state/capsule_state.dart';
import '../ui/capsule_widget.dart';
import '../ui/error_action_widget.dart';
import '../ui/init_wizard/init_wizard.dart';

/// Nextalk 应用根组件
/// Story 3-6: 完整业务流串联
/// Story 3-7: 错误状态操作按钮集成 + 初始化向导路由
///
/// 使用 StreamBuilder 绑定状态流到 UI，自动处理生命周期。
/// 根据模型状态路由到初始化向导或正常胶囊 UI。
class NextalkApp extends StatefulWidget {
  const NextalkApp({
    super.key,
    required this.stateController,
    required this.modelManager,
  });

  /// 状态控制器 (由 main.dart 注入)
  final StreamController<CapsuleStateData> stateController;

  /// 模型管理器 (由 main.dart 注入)
  final ModelManager modelManager;

  @override
  State<NextalkApp> createState() => _NextalkAppState();
}

class _NextalkAppState extends State<NextalkApp> {
  /// 是否需要显示初始化向导
  late bool _needsInit;

  @override
  void initState() {
    super.initState();
    // Story 3-7 AC1: 首次运行检测到模型缺失时显示初始化向导
    _needsInit = !widget.modelManager.isModelReady;
  }

  /// 初始化向导完成回调
  void _onInitCompleted() {
    // 重置窗口尺寸为正常胶囊尺寸
    WindowService.instance.resetToNormalSize();
    setState(() {
      _needsInit = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: 'Nextalk Voice Capsule',
      theme: ThemeData.dark().copyWith(
        scaffoldBackgroundColor: Colors.transparent,
      ),
      home: Scaffold(
        backgroundColor: Colors.transparent,
        // Story 3-7: 根据初始化状态路由 UI
        body: _needsInit
            ? _buildInitWizard()
            : _buildCapsuleUI(),
      ),
    );
  }

  /// 构建初始化向导 (AC1-AC7)
  Widget _buildInitWizard() {
    return InitWizard(
      modelManager: widget.modelManager,
      onCompleted: _onInitCompleted,
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

        // 状态相关的显示逻辑由 CapsuleWidget 统一处理
        // NextalkApp 只负责传递状态和控制 showHint
        final showHint = state.state == CapsuleState.listening &&
            state.recognizedText.isEmpty;

        // 错误状态的提示文字
        final hintText = state.state == CapsuleState.error
            ? state.displayMessage
            : '正在聆听...';

        // Story 3-7: 错误状态时显示操作按钮
        final isErrorWithActions = state.state == CapsuleState.error &&
            _shouldShowErrorActions(state.errorType);

        return Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            CapsuleWidget(
              text: state.recognizedText,
              showHint: showHint,
              hintText: hintText,
              // 传递完整状态，CapsuleWidget 内部处理显示逻辑
              stateData: state,
            ),

            // Story 3-7: 错误操作按钮 (在胶囊下方显示)
            if (isErrorWithActions)
              Padding(
                padding: const EdgeInsets.only(top: 12),
                child: _buildErrorActions(context, state),
              ),
          ],
        );
      },
    );
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
  List<ErrorAction> _getActionsForError(BuildContext context, CapsuleStateData state) {
    final errorType = state.errorType;
    if (errorType == null) return [];

    switch (errorType) {
      // 音频设备错误
      case CapsuleErrorType.audioNoDevice:
      case CapsuleErrorType.audioDeviceBusy:
      case CapsuleErrorType.audioInitFailed:
        return [
          ErrorAction(
            label: '刷新检测',
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
              label: '复制文本',
              onPressed: () => _copyPreservedText(context, state.preservedText!),
            ),
          ErrorAction(
            label: '关闭',
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
              label: '复制文本',
              onPressed: () => _copyPreservedText(context, state.preservedText!),
            ),
            ErrorAction(
              label: '重试提交',
              onPressed: () => HotkeyController.instance.retrySubmit(),
              isPrimary: true,
            ),
            ErrorAction(
              label: '放弃',
              onPressed: () => HotkeyController.instance.discardPreservedText(),
            ),
          ] else
            ErrorAction(
              label: '关闭',
              onPressed: () => HotkeyController.instance.dismissError(),
              isPrimary: true,
            ),
        ];

      // 模型错误 (AC8-AC10)
      case CapsuleErrorType.modelNotFound:
      case CapsuleErrorType.modelIncomplete:
        return [
          ErrorAction(
            label: '重新下载',
            onPressed: () {
              // TODO: 触发初始化向导
              HotkeyController.instance.dismissError();
            },
            isPrimary: true,
          ),
          ErrorAction(
            label: '关闭',
            onPressed: () => HotkeyController.instance.dismissError(),
          ),
        ];

      // 模型损坏 (AC8: 删除并重新下载)
      case CapsuleErrorType.modelCorrupted:
        return [
          ErrorAction(
            label: '删除并重新下载',
            onPressed: () async {
              await widget.modelManager.deleteModel();
              HotkeyController.instance.dismissError();
              // TODO: 触发初始化向导
            },
            isPrimary: true,
          ),
          ErrorAction(
            label: '关闭',
            onPressed: () => HotkeyController.instance.dismissError(),
          ),
        ];

      // 模型加载失败 (AC9: 显示具体原因)
      case CapsuleErrorType.modelLoadFailed:
        return [
          ErrorAction(
            label: '重试',
            onPressed: () => HotkeyController.instance.retryRecording(),
            isPrimary: true,
          ),
          ErrorAction(
            label: '关闭',
            onPressed: () => HotkeyController.instance.dismissError(),
          ),
        ];

      default:
        return [
          ErrorAction(
            label: '关闭',
            onPressed: () => HotkeyController.instance.dismissError(),
            isPrimary: true,
          ),
        ];
    }
  }

  /// 复制保护的文本到剪贴板
  Future<void> _copyPreservedText(BuildContext context, String text) async {
    await Clipboard.setData(ClipboardData(text: text));
    if (context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('文本已复制到剪贴板'),
          duration: Duration(seconds: 2),
        ),
      );
    }
  }
}
