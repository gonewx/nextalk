import 'dart:async';
import 'dart:io';
import 'package:flutter_test/flutter_test.dart';
import 'package:voice_capsule/constants/settings_constants.dart';
import 'package:voice_capsule/l10n/app_localizations_en.dart';
import 'package:voice_capsule/l10n/app_localizations_zh.dart';
import 'package:voice_capsule/services/asr/asr_engine.dart';
import 'package:voice_capsule/services/audio_inference_pipeline.dart';
import 'package:voice_capsule/services/model_manager.dart';
import 'package:voice_capsule/services/settings_service.dart';

void main() {
  test('YAML 参数传入预热和运行期共用的配置构造', () async {
    final dir = Directory.systemTemp.createTempSync('nextalk_qwen_settings_');
    final file = File('${dir.path}/settings.yaml');
    final settings = SettingsService.instance;
    try {
      await IOOverrides.runZoned(() async {
        file.writeAsStringSync('''model:
  engine: qwen3_asr
  qwen3_asr:
    num_threads: 4
    max_new_tokens: 256
    hotwords: "Nextalk,语音输入"
    custom_url: "https://example.com/model.tar.bz2"
''');
        await settings.reload();
        final config = AudioInferencePipeline.buildEngineConfig(
          engineType: ASREngineType.qwen3Asr,
          modelManager: ModelManager(),
        ) as Qwen3AsrConfig;
        expect(config.numThreads, 4);
        expect(config.maxNewTokens, 256);
        expect(config.hotwords, 'Nextalk,语音输入');
        expect(config.modelDir, endsWith('/qwen3_asr'));
        expect(config.vadModelPath, endsWith('/vad/silero_vad.onnx'));
        expect(settings.qwen3AsrCustomUrl, 'https://example.com/model.tar.bz2');
        for (final section in [
          '    num_threads: -1\n    max_new_tokens: 999\n    hotwords: []',
          '    num_threads: wrong\n    max_new_tokens: false',
        ]) {
          file.writeAsStringSync('model:\n  qwen3_asr:\n$section\n');
          await settings.reload();
          expect(settings.qwen3AsrNumThreads, 2);
          expect(settings.qwen3AsrMaxNewTokens, 128);
          expect(settings.qwen3AsrHotwords, '');
        }
        file.writeAsStringSync('model:\n  qwen3_asr: invalid\n');
        await settings.reload();
        expect(settings.qwen3AsrNumThreads, 2);
      },
          createFile: (path) => Zone.root.run(() => File(
              path == SettingsConstants.settingsFilePath ? file.path : path)));
    } finally {
      await settings.reload();
      dir.deleteSync(recursive: true);
    }
  });
  test('配置模板和两种语言均包含 Qwen3-ASR', () {
    expect(SettingsConstants.defaultSettingsYaml, contains('qwen3_asr:'));
    expect(
        SettingsConstants.defaultSettingsYaml, contains('max_new_tokens: 128'));
    expect(AppLocalizationsZh().trayEngineQwen3Asr, contains('离线'));
    expect(AppLocalizationsEn().trayEngineQwen3Asr, contains('Offline'));
    expect(ModelConfigs.qwen3Asr.sha256,
        '393f8a14e2f5fb96746aaab342997a40641001fbd5bf9592a080a8329178ee96');
  });
}
