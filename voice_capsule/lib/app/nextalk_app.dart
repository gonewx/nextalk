import 'dart:async';
import 'package:flutter/material.dart';
import '../state/capsule_state.dart';
import '../ui/capsule_widget.dart';

/// Nextalk 应用根组件
/// Story 3-6: 完整业务流串联
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

            return CapsuleWidget(
              text: state.recognizedText,
              showHint: showHint,
              hintText: hintText,
              // 传递完整状态，CapsuleWidget 内部处理显示逻辑
              stateData: state,
            );
          },
        ),
      ),
    );
  }
}
