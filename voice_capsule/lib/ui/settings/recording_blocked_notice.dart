import 'package:flutter/material.dart';

/// 不抢走草稿、不堆叠弹窗，解释快捷键为何暂时不能开始录音。
class RecordingBlockedNotice extends StatelessWidget {
  const RecordingBlockedNotice(
      {super.key,
      required this.isZh,
      required this.busy,
      required this.editing,
      required this.modelReady,
      this.onCloseSettings,
      this.onDismiss});
  final bool isZh;
  final bool busy;
  final bool editing;
  final bool modelReady;
  final VoidCallback? onCloseSettings;
  final VoidCallback? onDismiss;
  String tr(String zh, String en) => isZh ? zh : en;

  @override
  Widget build(BuildContext context) {
    final message = busy
        ? tr('正在处理设置任务，暂时无法录音。请等待完成，或在下载页取消任务。',
            'Settings are busy. Wait for completion or cancel the download before recording.')
        : editing
            ? tr('设置窗口打开时暂不录音。请先保存或取消当前配置，再关闭设置，点击目标输入框后按快捷键录音。',
                'Save or cancel your changes, then close settings. Click the target input field and press the shortcut to record.')
            : !modelReady
                ? tr('当前模型尚未就绪，请先配置或下载并选择模型，再开始录音。',
                    'The current model is not ready. Configure or download and select a model first.')
                : tr('请先关闭设置，点击 IDE 或其他应用中的目标输入框，再按快捷键开始录音。',
                    'Close settings, click the target input field in your IDE or another app, then press the shortcut to record.');
    return TweenAnimationBuilder<Color?>(
        tween: ColorTween(
            begin: const Color(0xFF765128), end: const Color(0xFF352B21)),
        duration: const Duration(milliseconds: 900),
        builder: (context, color, child) =>
            ColoredBox(color: color!, child: child!),
        child: Semantics(
            liveRegion: true,
            child: Container(
              key: const ValueKey('recording-blocked-notice'),
              padding: const EdgeInsets.fromLTRB(16, 8, 8, 8),
              child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Padding(
                              padding: EdgeInsets.only(top: 10),
                              child: Icon(Icons.mic_off_outlined,
                                  color: Colors.orangeAccent, size: 22)),
                          const SizedBox(width: 12),
                          Expanded(
                              child: Padding(
                                  padding:
                                      const EdgeInsets.symmetric(vertical: 10),
                                  child: Text(message))),
                          IconButton(
                              tooltip: tr('收起提示', 'Dismiss'),
                              onPressed: onDismiss,
                              icon: const Icon(Icons.close, size: 18)),
                        ]),
                    if (!busy && !editing && modelReady)
                      Align(
                          alignment: Alignment.centerRight,
                          child: FilledButton.icon(
                              onPressed: onCloseSettings,
                              icon: const Icon(Icons.close, size: 18),
                              label: Text(tr('关闭设置', 'Close settings')))),
                  ]),
            )));
  }
}
