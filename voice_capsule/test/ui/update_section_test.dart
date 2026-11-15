import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:voice_capsule/services/update_service.dart';
import 'package:voice_capsule/ui/settings/update_section.dart';

class WidgetUpdater extends UpdateService {
  WidgetUpdater({super.currentVersion = '0.4.1'});
  int installs = 0;
  late Completer<void> completion;
  @override
  Future<void> install({required bool Function() canInstall}) async {
    completion = Completer<void>();
    installs++;
    phase = UpdatePhase.downloading;
    notifyListeners();
    await completion.future;
    phase = UpdatePhase.installed;
    notifyListeners();
  }
}

void main() {
  late WidgetUpdater updater;
  late List<bool> busy;
  setUp(() {
    updater = WidgetUpdater();
    busy = [];
  });
  tearDown(() {
    updater.dispose();
  });
  Future<void> show(WidgetTester tester) => tester.pumpWidget(MaterialApp(
      home: Scaffold(
          body: SingleChildScrollView(
              child: UpdateSection(
                  isZh: true, service: updater, onBusyChanged: busy.add)))));
  void available() {
    updater.phase = UpdatePhase.available;
    updater.release = const UpdateRelease(
        version: '0.5.0',
        notes: '改进识别',
        name: 'package.deb',
        url: 'https://example.test/package',
        digest: 'test',
        size: 1);
  }

  testWidgets('取消确认不下载、不锁定窗口', (tester) async {
    available();
    await show(tester);
    await tester.tap(find.text('立即升级'));
    await tester.pumpAndSettle();
    expect(find.text('升级到 0.5.0'), findsOneWidget);
    await tester.tap(find.text('稍后'));
    await tester.pumpAndSettle();
    expect(updater.installs, 0);
    expect(busy, isEmpty);
  });
  testWidgets('确认后显示下载进度，安装结束解除关闭保护并提示重启', (tester) async {
    available();
    await show(tester);
    await tester.tap(find.text('立即升级'));
    await tester.pumpAndSettle();
    await tester.tap(find.widgetWithText(FilledButton, '立即升级').last);
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));
    expect(updater.installs, 1);
    expect(busy, [true]);
    expect(find.text('正在下载安装包…'), findsOneWidget);
    expect(find.text('取消下载'), findsOneWidget);
    updater.completion.complete();
    await tester.pumpAndSettle();
    expect(busy, [true, false]);
    expect(find.text('升级成功，请退出并重新打开 Nextalk。'), findsOneWidget);
    expect(find.text('立即升级'), findsNothing);
  });
  testWidgets('不兼容安装包保留手动入口且禁用安装', (tester) async {
    updater.phase = UpdatePhase.available;
    updater.release = const UpdateRelease(version: '0.5.0', notes: '');
    await show(tester);
    expect(
        tester
            .widget<FilledButton>(find.widgetWithText(FilledButton, '立即升级'))
            .onPressed,
        isNull);
    expect(find.text('发布页面'), findsOneWidget);
  });
  testWidgets('开发构建禁用检查', (tester) async {
    updater.dispose();
    updater = WidgetUpdater(currentVersion: 'dev');
    await show(tester);
    expect(
        tester
            .widget<OutlinedButton>(find.widgetWithText(OutlinedButton, '检查更新'))
            .onPressed,
        isNull);
    expect(find.text('开发构建不支持自动升级，请使用正式安装包。'), findsOneWidget);
  });
}
