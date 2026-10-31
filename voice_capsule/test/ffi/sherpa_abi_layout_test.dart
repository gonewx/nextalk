import 'dart:ffi';
import 'package:flutter_test/flutter_test.dart';
import 'package:ffi/ffi.dart';
import 'package:voice_capsule/ffi/sherpa_offline_bindings.dart';
import 'package:voice_capsule/ffi/sherpa_onnx_bindings.dart';
import 'package:voice_capsule/ffi/sherpa_vad_bindings.dart';

void main() {
  test('全部 FFI 结构体大小与 sherpa-onnx v2.0.1 Linux x64 C API 一致', () {
    // 期望值由对应版本 c-api.h 的 C sizeof 实测得出。
    expect(sizeOf<IntPtr>(), 8);
    expect(sizeOf<SherpaOnnxFeatureConfig>(), 8,
        reason: 'SherpaOnnxFeatureConfig');
    expect(sizeOf<SherpaOnnxOnlineTransducerModelConfig>(), 24,
        reason: 'SherpaOnnxOnlineTransducerModelConfig');
    expect(sizeOf<SherpaOnnxOnlineParaformerModelConfig>(), 16,
        reason: 'SherpaOnnxOnlineParaformerModelConfig');
    expect(sizeOf<SherpaOnnxOnlineZipformer2CtcModelConfig>(), 8,
        reason: 'SherpaOnnxOnlineZipformer2CtcModelConfig');
    expect(sizeOf<SherpaOnnxOnlineNemoCtcModelConfig>(), 8,
        reason: 'SherpaOnnxOnlineNemoCtcModelConfig');
    expect(sizeOf<SherpaOnnxOnlineToneCtcModelConfig>(), 8,
        reason: 'SherpaOnnxOnlineToneCtcModelConfig');
    expect(sizeOf<SherpaOnnxOnlineCtcFstDecoderConfig>(), 16,
        reason: 'SherpaOnnxOnlineCtcFstDecoderConfig');
    expect(sizeOf<SherpaOnnxHomophoneReplacerConfig>(), 24,
        reason: 'SherpaOnnxHomophoneReplacerConfig');
    expect(sizeOf<SherpaOnnxOnlineModelConfig>(), 136,
        reason: 'SherpaOnnxOnlineModelConfig');
    expect(sizeOf<SherpaOnnxOnlineRecognizerConfig>(), 272,
        reason: 'SherpaOnnxOnlineRecognizerConfig');
    expect(sizeOf<SherpaOnnxOfflineSenseVoiceModelConfig>(), 24,
        reason: 'SherpaOnnxOfflineSenseVoiceModelConfig');
    expect(sizeOf<SherpaOnnxOfflineTransducerModelConfig>(), 24,
        reason: 'SherpaOnnxOfflineTransducerModelConfig');
    expect(sizeOf<SherpaOnnxOfflineParaformerModelConfig>(), 8,
        reason: 'SherpaOnnxOfflineParaformerModelConfig');
    expect(sizeOf<SherpaOnnxOfflineNemoEncDecCtcModelConfig>(), 8,
        reason: 'SherpaOnnxOfflineNemoEncDecCtcModelConfig');
    expect(sizeOf<SherpaOnnxOfflineWhisperModelConfig>(), 48,
        reason: 'SherpaOnnxOfflineWhisperModelConfig');
    expect(sizeOf<SherpaOnnxOfflineTdnnModelConfig>(), 8,
        reason: 'SherpaOnnxOfflineTdnnModelConfig');
    expect(sizeOf<SherpaOnnxOfflineMoonshineModelConfig>(), 40,
        reason: 'SherpaOnnxOfflineMoonshineModelConfig');
    expect(sizeOf<SherpaOnnxOfflineFireRedAsrModelConfig>(), 16,
        reason: 'SherpaOnnxOfflineFireRedAsrModelConfig');
    expect(sizeOf<SherpaOnnxOfflineDolphinModelConfig>(), 8,
        reason: 'SherpaOnnxOfflineDolphinModelConfig');
    expect(sizeOf<SherpaOnnxOfflineZipformerCtcModelConfig>(), 8,
        reason: 'SherpaOnnxOfflineZipformerCtcModelConfig');
    expect(sizeOf<SherpaOnnxOfflineCanaryModelConfig>(), 40,
        reason: 'SherpaOnnxOfflineCanaryModelConfig');
    expect(sizeOf<SherpaOnnxOfflineWenetCtcModelConfig>(), 8,
        reason: 'SherpaOnnxOfflineWenetCtcModelConfig');
    expect(sizeOf<SherpaOnnxOfflineOmnilingualAsrCtcModelConfig>(), 8,
        reason: 'SherpaOnnxOfflineOmnilingualAsrCtcModelConfig');
    expect(sizeOf<SherpaOnnxOfflineHomophoneReplacerConfig>(), 24,
        reason: 'SherpaOnnxOfflineHomophoneReplacerConfig');
    expect(sizeOf<SherpaOnnxOfflineMedAsrCtcModelConfig>(), 8,
        reason: 'SherpaOnnxOfflineMedAsrCtcModelConfig');
    expect(sizeOf<SherpaOnnxOfflineFunASRNanoModelConfig>(), 88,
        reason: 'SherpaOnnxOfflineFunASRNanoModelConfig');
    expect(sizeOf<SherpaOnnxOfflineFireRedAsrCtcModelConfig>(), 8,
        reason: 'SherpaOnnxOfflineFireRedAsrCtcModelConfig');
    expect(sizeOf<SherpaOnnxOfflineQwen3ASRModelConfig>(), 64,
        reason: 'SherpaOnnxOfflineQwen3ASRModelConfig');
    expect(sizeOf<SherpaOnnxOfflineCohereTranscribeModelConfig>(), 32,
        reason: 'SherpaOnnxOfflineCohereTranscribeModelConfig');
    expect(sizeOf<SherpaOnnxOfflineCtcFstDecoderConfig>(), 16,
        reason: 'SherpaOnnxOfflineCtcFstDecoderConfig');
    expect(sizeOf<SherpaOnnxOfflineModelConfig>(), 504,
        reason: 'SherpaOnnxOfflineModelConfig');
    expect(sizeOf<SherpaOnnxOfflineLMConfig>(), 16,
        reason: 'SherpaOnnxOfflineLMConfig');
    expect(sizeOf<SherpaOnnxOfflineRecognizerConfig>(), 624,
        reason: 'SherpaOnnxOfflineRecognizerConfig');
    expect(sizeOf<SherpaOnnxFeatureConfigOffline>(), 8,
        reason: 'SherpaOnnxFeatureConfigOffline');
    expect(sizeOf<SherpaOnnxOfflineRecognizerResult>(), 128,
        reason: 'SherpaOnnxOfflineRecognizerResult');
    expect(sizeOf<SherpaOnnxSileroVadModelConfig>(), 32,
        reason: 'SherpaOnnxSileroVadModelConfig');
    expect(sizeOf<SherpaOnnxTenVadModelConfig>(), 32,
        reason: 'SherpaOnnxTenVadModelConfig');
    expect(sizeOf<SherpaOnnxVadModelConfig>(), 88,
        reason: 'SherpaOnnxVadModelConfig');
    expect(sizeOf<SherpaOnnxSpeechSegment>(), 24,
        reason: 'SherpaOnnxSpeechSegment');
  });
  test('新增字段偏移与 C offsetof 一致，VAD 起点保留 64 位', () {
    using((arena) {
      final model = arena<SherpaOnnxOfflineModelConfig>();
      final marker = Pointer<Utf8>.fromAddress(0x12345678);
      model.ref.senseVoice.model = marker;
      model.ref.qwen3Asr.convFrontend = marker;
      model.ref.cohereTranscribe.encoder = marker;
      for (final offset in [152, 408, 472]) {
        expect(
            (model.cast<Uint8>() + offset).cast<Pointer<Utf8>>().value, marker);
      }
      final offline = arena<SherpaOnnxOfflineRecognizerConfig>();
      offline.ref.hr.lexicon = marker;
      offline.ref.ctcFstDecoderConfig.graph = marker;
      expect((offline.cast<Uint8>() + 592).cast<Pointer<Utf8>>().value, marker);
      expect((offline.cast<Uint8>() + 608).cast<Pointer<Utf8>>().value, marker);
      final qwen = arena<SherpaOnnxOfflineQwen3ASRModelConfig>();
      qwen.ref.hotwords = marker;
      expect((qwen.cast<Uint8>() + 56).cast<Pointer<Utf8>>().value, marker);
      final result = arena<SherpaOnnxOfflineRecognizerResult>();
      result.ref.segmentCount = 7;
      expect((result.cast<Uint8>() + 120).cast<Int32>().value, 7);
      final online = arena<SherpaOnnxOnlineRecognizerConfig>();
      online.ref.hr.dictDir = marker;
      expect((online.cast<Uint8>() + 248).cast<Pointer<Utf8>>().value, marker);
      final vad = arena<SherpaOnnxVadModelConfig>();
      vad.ref.tenVad.model = marker;
      expect((vad.cast<Uint8>() + 56).cast<Pointer<Utf8>>().value, marker);
      final segment = arena<SherpaOnnxSpeechSegment>();
      segment.ref.start = 0x100000001;
      expect(segment.cast<Int64>().value, 0x100000001);
    });
  });
}
