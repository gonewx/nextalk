import 'dart:io';
import 'package:flutter_test/flutter_test.dart';
import 'package:yaml/yaml.dart';
import 'package:voice_capsule/services/deepseek_settings_store.dart';

void main() {
  for (final source in [
    'model:\n  engine: qwen3_asr\n  qwen3_asr:\n    num_threads: 2\ntext:\n  enabled: true\n',
    'model: {engine: qwen3_asr}\ntext: {enabled: true}\n',
    'model:\n    engine: qwen3_asr\n    deepseek: null\ntext: {enabled: true}\n',
    '{model: {engine: qwen3_asr}, text: {enabled: true}}',
    'model:\n  engine: qwen3_asr\n  deepseek:\n    api_key: old\ntext:\n  enabled: true\n',
    'model:\n  engine: qwen3_asr\n  deepseek: {}\ntext:\n  enabled: true\n',
    'model:\n  engine: qwen3_asr\n  deepseek:\n    other: true\ntext:\n  enabled: true\n',
  ]) {
    test('save preserves unrelated YAML: $source', () {
      final updated = DeepSeekSettingsStore.update(source, ' new:#"key ');
      final data = loadYaml(updated);
      expect(data['model']['engine'], 'qwen3_asr');
      expect(data['model']['deepseek']['api_key'], 'new:#"key');
      expect(data['text']['enabled'], true);
    });
  }
  test('missing model and empty map are supported', () {
    final data = loadYaml(
        DeepSeekSettingsStore.update('text: {enabled: true}\n', 'key'));
    expect(data['model']['deepseek']['api_key'], 'key');
  });
  test('empty flow root supports first save', () {
    expect(
        loadYaml(DeepSeekSettingsStore.update('{}', 'key'))['model']['deepseek']
            ['api_key'],
        'key');
  });
  test('atomic save restricts file access', () async {
    final dir = await Directory.systemTemp.createTemp('deepseek-settings-test');
    addTearDown(() => dir.delete(recursive: true));
    final file = File('${dir.path}/settings.yaml');
    await file.writeAsString('model: {engine: zipformer}\n');
    await DeepSeekSettingsStore.save(file, 'test-key');
    expect((await file.stat()).mode & 0x1ff, 0x180);
    expect(loadYaml(await file.readAsString())['model']['deepseek']['api_key'],
        'test-key');
    expect((await dir.list().toList()).length, 1);
  });
  test('saving engine after API key keeps both values', () async {
    final dir = await Directory.systemTemp.createTemp('deepseek-engine-test');
    addTearDown(() => dir.delete(recursive: true));
    final file = File('${dir.path}/settings.yaml');
    await file.writeAsString('model: {engine: qwen3_asr}\n');
    await DeepSeekSettingsStore.save(file, 'test-key');
    await DeepSeekSettingsStore.saveEngine(file, 'deepseek');
    final data = loadYaml(await file.readAsString());
    expect(data['model']['engine'], 'deepseek');
    expect(data['model']['deepseek']['api_key'], 'test-key');
    expect((await file.stat()).mode & 0x1ff, 0x180);
  });
  test('invalid config does not overwrite original', () async {
    final dir = await Directory.systemTemp.createTemp('deepseek-settings-test');
    addTearDown(() => dir.delete(recursive: true));
    final file = File('${dir.path}/settings.yaml');
    await file.writeAsString('model: [broken');
    await expectLater(
        DeepSeekSettingsStore.save(file, 'key'), throwsA(anything));
    expect(await file.readAsString(), 'model: [broken');
  });
}
