import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:voice_capsule/ui/settings/recording_blocked_notice.dart';

void main() {
  testWidgets(
      'ready state closes settings and explains explicit input selection',
      (tester) async {
    var closes = 0;
    var dismisses = 0;
    await tester.pumpWidget(MaterialApp(
        home: Scaffold(
            body: RecordingBlockedNotice(
      isZh: true,
      busy: false,
      editing: false,
      modelReady: true,
      onCloseSettings: () => closes++,
      onDismiss: () => dismisses++,
    ))));
    await tester.tap(find.text('关闭设置'));
    expect(closes, 1);
    expect(find.textContaining('点击 IDE'), findsOneWidget);
    expect(find.text('关闭设置并开始录音'), findsNothing);
    await tester.tap(find.byTooltip('收起提示'));
    expect(dismisses, 1);
  });
  testWidgets(
      'busy, editing and missing-model states do not discard work or record',
      (tester) async {
    for (final scenario in [
      (true, false, true, '正在处理设置任务'),
      (false, true, true, '请先保存或取消'),
      (false, false, false, '当前模型尚未就绪')
    ]) {
      await tester.pumpWidget(MaterialApp(
          home: Scaffold(
              body: RecordingBlockedNotice(
        isZh: true,
        busy: scenario.$1,
        editing: scenario.$2,
        modelReady: scenario.$3,
        onCloseSettings: () => fail('must not discard unfinished work'),
      ))));
      expect(find.textContaining(scenario.$4), findsOneWidget);
      expect(find.byType(FilledButton), findsNothing);
    }
  });
}
