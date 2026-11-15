import 'dart:async';
import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:voice_capsule/services/asr/deepseek_asr_client.dart';
import 'package:voice_capsule/ui/deepseek_settings_view.dart';

class FakeClient extends DeepSeekAsrClient {
  final pending = <Completer<void>>[];
  final keys = <String>[];
  final tokens = <CancelToken?>[];
  @override
  Future<void> testConnection(String apiKey, {CancelToken? cancelToken}) {
    keys.add(apiKey);
    tokens.add(cancelToken);
    final c = Completer<void>();
    pending.add(c);
    return c.future;
  }
}

void main() {
  testWidgets('draft tests, changes invalidate result, save is immediate',
      (tester) async {
    final client = FakeClient();
    addTearDown(client.close);
    String? saved;
    await tester.pumpWidget(MaterialApp(
        home: Scaffold(
            body: DeepSeekSettingsView(
      initialKey: '',
      fromEnvironment: false,
      isZh: true,
      client: client,
      onSave: (key) async {
        saved = key;
      },
      onCancel: () {},
    ))));
    expect(tester.widget<FilledButton>(find.byType(FilledButton)).onPressed,
        isNull);
    await tester.enterText(find.byType(TextField), 'first-key');
    await tester.pump();
    await tester.tap(find.text('测试连接'));
    await tester.pump();
    expect(client.keys, ['first-key']);
    expect(saved, isNull);
    await tester.enterText(find.byType(TextField), 'second-key');
    expect(client.tokens.first!.isCancelled, true);
    client.pending.first.complete();
    await tester.pump();
    expect(find.text('连接成功，API Key 可用'), findsNothing);
    await tester.tap(find.text('测试连接'));
    await tester.pump();
    client.pending.last.complete();
    await tester.pump();
    expect(find.text('连接成功，API Key 可用'), findsOneWidget);
    await tester.tap(find.text('保存配置'));
    await tester.pump();
    expect(saved, 'second-key');
  });
  testWidgets('failure is visible and cancel does not save', (tester) async {
    final client = FakeClient();
    addTearDown(client.close);
    var saved = false;
    var cancelled = false;
    await tester.pumpWidget(MaterialApp(
        home: Scaffold(
            body: DeepSeekSettingsView(
      initialKey: 'key',
      fromEnvironment: true,
      isZh: true,
      client: client,
      onSave: (_) async {
        saved = true;
      },
      onCancel: () {
        cancelled = true;
      },
    ))));
    await tester.tap(find.text('测试连接'));
    await tester.pump();
    client.pending.first.completeError(const DeepSeekException('auth'));
    await tester.pump();
    expect(find.text('API Key 无效，请检查配置'), findsOneWidget);
    await tester.tap(find.text('取消'));
    expect(cancelled, true);
    expect(saved, false);
  });
  testWidgets('save failure keeps draft and controls usable', (tester) async {
    await tester.pumpWidget(MaterialApp(
        home: Scaffold(
            body: DeepSeekSettingsView(
      initialKey: 'key',
      fromEnvironment: false,
      isZh: true,
      onSave: (_) async {
        throw StateError('cannot save');
      },
      onCancel: () {},
    ))));
    await tester.tap(find.text('保存配置'));
    await tester.pump();
    expect(find.text('保存失败，请重试'), findsOneWidget);
    expect(tester.widget<TextField>(find.byType(TextField)).controller!.text,
        'key');
    expect(tester.widget<FilledButton>(find.byType(FilledButton)).onPressed,
        isNotNull);
  });
  testWidgets('disposing cancels pending connection test', (tester) async {
    final client = FakeClient();
    addTearDown(client.close);
    await tester.pumpWidget(MaterialApp(
        home: Scaffold(
            body: DeepSeekSettingsView(
      initialKey: 'key',
      fromEnvironment: false,
      isZh: true,
      client: client,
      onSave: (_) async {},
      onCancel: () {},
    ))));
    await tester.tap(find.text('测试连接'));
    await tester.pump();
    await tester.pumpWidget(const SizedBox());
    expect(client.tokens.first!.isCancelled, true);
    client.pending.first.complete();
    await tester.pump();
    expect(tester.takeException(), isNull);
  });
}
