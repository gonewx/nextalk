import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:voice_capsule/constants/settings_constants.dart';
import 'package:voice_capsule/services/model_manager.dart';
import 'package:voice_capsule/services/language_service.dart';
import 'package:voice_capsule/ui/settings/settings_window.dart';

class ReadyModels extends ModelManager {
  @override
  bool isEngineReady(EngineType type) => true;
}

void main() {
  for (final size in [
    const Size(420, 360),
    const Size(320, 280),
    const Size(1200, 900)
  ]) {
    for (final general in [false, true]) {
      testWidgets(
          '${size.width}×${size.height} ${general ? "设置" : "模型"}页面支持大字体和滚动',
          (tester) async {
        tester.view.physicalSize = size;
        tester.view.devicePixelRatio = 1;
        addTearDown(tester.view.resetPhysicalSize);
        addTearDown(tester.view.resetDevicePixelRatio);
        LanguageService.instance.localeNotifier.value = const Locale('en');
        addTearDown(() =>
            LanguageService.instance.localeNotifier.value = const Locale('zh'));
        await tester.pumpWidget(MaterialApp(
            builder: (context, child) => MediaQuery(
                data: MediaQuery.of(context)
                    .copyWith(textScaler: const TextScaler.linear(1.8)),
                child: child!),
            home: SettingsWindow(
                modelManager: ReadyModels(),
                onClose: () {},
                onBusyChanged: (_) {},
                initialGeneral: general)));
        await tester.pump();
        expect(tester.takeException(), isNull);
        await tester.ensureVisible(find.byType(ListView).first);
        await tester.pump();
        if (general) {
          await tester.scrollUntilVisible(find.text('Version and updates'), 150,
              scrollable: find
                  .descendant(
                      of: find.byType(ListView).first,
                      matching: find.byType(Scrollable))
                  .first);
          expect(tester.takeException(), isNull);
          expect(find.text('Version and updates'), findsOneWidget);
        } else {
          await tester.scrollUntilVisible(
              find.byKey(const ValueKey('manage-sensevoice')), 150,
              scrollable: find
                  .descendant(
                      of: find.byType(ListView).first,
                      matching: find.byType(Scrollable))
                  .first);
          expect(tester.takeException(), isNull);
          expect(
              find.byKey(const ValueKey('manage-sensevoice')), findsOneWidget);
        }
      });
    }
  }
  testWidgets('窄窗口关闭设置提示和云端表单不会溢出', (tester) async {
    tester.view.physicalSize = const Size(420, 360);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    await tester.pumpWidget(MaterialApp(
        home: SettingsWindow(
            modelManager: ReadyModels(),
            initialEngine: EngineType.deepseek,
            recordingRequested: true,
            onClose: () {},
            onBusyChanged: (_) {})));
    await tester.pump(const Duration(seconds: 1));
    expect(tester.takeException(), isNull);
  });
  testWidgets('窗口缩放保留未保存的云端配置草稿', (tester) async {
    tester.view.physicalSize = const Size(1000, 800);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    await tester.pumpWidget(MaterialApp(
        home: SettingsWindow(
            modelManager: ReadyModels(),
            initialEngine: EngineType.deepseek,
            onClose: () {},
            onBusyChanged: (_) {})));
    await tester.enterText(find.byType(TextField), 'draft-key');
    tester.view.physicalSize = const Size(420, 360);
    await tester.pump();
    expect(tester.takeException(), isNull);
    expect(tester.widget<TextField>(find.byType(TextField)).controller!.text,
        'draft-key');
  });
}
