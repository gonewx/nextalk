import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:voice_capsule/constants/settings_constants.dart';
import 'package:voice_capsule/ui/settings/model_selection_view.dart';

void main() {
  testWidgets('loading model shows progress and blocks duplicate actions',
      (tester) async {
    var actions = 0;
    await tester.pumpWidget(MaterialApp(
        home: Scaffold(
            body: ModelSelectionView(
      isZh: true,
      selected: EngineType.qwen3Asr,
      loading: EngineType.deepseek,
      readiness: const {EngineType.deepseek: true},
      busy: true,
      onSelect: (_) => actions++,
      onManage: (_) => actions++,
    ))));
    expect(find.text('正在加载…'), findsOneWidget);
    expect(find.byType(CircularProgressIndicator), findsOneWidget);
    await tester.tap(find.byKey(const ValueKey('select-deepseek')));
    await tester.tap(find.byKey(const ValueKey('manage-deepseek')));
    expect(actions, 0);
  });

  testWidgets(
      'unready models cannot be selected but can be configured or downloaded',
      (tester) async {
    EngineType? selected;
    EngineType? managed;
    await tester.pumpWidget(MaterialApp(
        home: Scaffold(
            body: ModelSelectionView(
      isZh: true,
      selected: EngineType.qwen3Asr,
      readiness: const {EngineType.qwen3Asr: true},
      onSelect: (type) {
        selected = type;
      },
      onManage: (type) {
        managed = type;
      },
    ))));
    final deep = find.byKey(const ValueKey('select-deepseek'));
    await tester.tap(deep);
    expect(selected, isNull);
    await tester.tap(find.byKey(const ValueKey('manage-deepseek')));
    expect(managed, EngineType.deepseek);
    await tester.tap(find.byKey(const ValueKey('manage-sensevoice')));
    expect(managed, EngineType.sensevoice);
    expect(selected, isNull);
  });
  testWidgets('configured model selection does not open its configuration',
      (tester) async {
    EngineType? selected;
    var managed = false;
    await tester.pumpWidget(MaterialApp(
        home: Scaffold(
            body: ModelSelectionView(
      isZh: true,
      selected: EngineType.qwen3Asr,
      readiness: const {EngineType.qwen3Asr: true, EngineType.deepseek: true},
      onSelect: (type) {
        selected = type;
      },
      onManage: (_) {
        managed = true;
      },
    ))));
    await tester.tap(find.byKey(const ValueKey('select-deepseek')));
    expect(selected, EngineType.deepseek);
    expect(managed, false);
  });
}
