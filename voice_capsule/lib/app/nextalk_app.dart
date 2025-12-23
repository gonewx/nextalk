import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../services/hotkey_controller.dart';
import '../state/capsule_state.dart';
import '../ui/capsule_widget.dart';
import '../ui/error_action_widget.dart';

/// Nextalk 应用根组件
/// Story 3-6: 完整业务流串联
/// Story 3-7: 错误状态操作按钮集成
///
/// 使用 StreamBuilder 绑定状态流到 UI，自动处理生命周期。
/// 替换 main.dart 中原有的 StatelessWidget 版本。
class NextalkApp extends StatelessWidget {
  const NextalkApp({
    super.key,
    required this.stateController,
  });

  /// 状态控制器 (由 main.dart 注入)
  final StreamController<CapsuleStateData> stateController;

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
        // 使用 StreamBuilder 自动管理订阅生命周期
        body: StreamBuilder<CapsuleStateData>(
          stream: stateController.stream,
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
        ),
      ),
    );
  }

  /// 判断是否应该显示错误操作按钮
  bool _shouldShowErrorActions(CapsuleErrorType? errorType) {
    if (errorType == null) return false;
    return switch (errorType) {
      CapsuleErrorType.audioNoDevice => true,
      CapsuleErrorType.audioDeviceBusy => true,
      CapsuleErrorType.audioDeviceLost => true,
      CapsuleErrorType.socketError => true,
      CapsuleErrorType.modelNotFound => true,
      CapsuleErrorType.modelIncomplete => true,
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
  List<ErrorAction> _getActionsForError(BuildContext context, CapsuleStateData state) {
    final errorType = state.errorType;
    if (errorType == null) return [];

    switch (errorType) {
      // 音频设备错误
      case CapsuleErrorType.audioNoDevice:
      case CapsuleErrorType.audioDeviceBusy:
        return [
          ErrorAction(
            label: '刷新检测',
            onPressed: () => HotkeyController.instance.dismissError(),
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

      // 模型错误
      case CapsuleErrorType.modelNotFound:
      case CapsuleErrorType.modelIncomplete:
        return [
          ErrorAction(
            label: '关闭',
            onPressed: () => HotkeyController.instance.dismissError(),
            isPrimary: true,
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
