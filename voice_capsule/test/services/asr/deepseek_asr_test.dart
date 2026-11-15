import 'dart:ffi';
import 'dart:async';
import 'package:dio/dio.dart';
import 'dart:typed_data';
import 'package:ffi/ffi.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:voice_capsule/services/asr/asr_engine.dart';
import 'package:voice_capsule/services/asr/deepseek_asr_client.dart';
import 'package:voice_capsule/services/asr/deepseek_asr_engine.dart';

class DelayedClient extends DeepSeekAsrClient {
  final calls = <Completer<String>>[];
  final sizes = <int>[];
  @override
  Future<String> transcribe(Uint8List wav, String apiKey,
      {CancelToken? cancelToken}) {
    sizes.add(wav.length);
    final pending = Completer<String>();
    calls.add(pending);
    return pending.future; // 故意不响应取消，模拟服务端迟到结果。
  }
}

void main() {
  test('120 second bound and late response isolation', () async {
    final client = DelayedClient();
    final engine = DeepSeekAsrEngine(client: client);
    await engine.initialize(const DeepSeekConfig(apiKey: 'test'));
    final p = calloc<Float>(DeepSeekAsrEngine.maxSamples + 1600);
    addTearDown(() {
      engine.dispose();
      calloc.free(p);
    });
    engine.acceptWaveform(16000, p, DeepSeekAsrEngine.maxSamples + 1600);
    expect(engine.atDurationLimit, true);
    final first = engine.finalizeUtterance();
    expect(client.sizes.first, 44 + 120 * 16000 * 2);
    engine.reset();
    engine.acceptWaveform(16000, p, 1600);
    final second = engine.finalizeUtterance();
    client.calls.first.complete('old');
    expect((await first).isEmpty, true);
    client.calls.last.complete('new');
    expect((await second).text, 'new');
  });
  test('PCM16 WAV encodes clipped samples and a valid header', () {
    final wav = encodePcm16Wav(Float32List.fromList([-2, 0, 1]));
    final data = ByteData.sublistView(wav);
    expect(String.fromCharCodes(wav.sublist(0, 4)), 'RIFF');
    expect(data.getUint32(24, Endian.little), 16000);
    expect(data.getUint32(40, Endian.little), 6);
    expect(data.getInt16(44, Endian.little), -32768);
    expect(data.getInt16(48, Endian.little), 32767);
  });
  test('cloud reset discards recording without sending a request', () async {
    final engine = DeepSeekAsrEngine();
    expect(await engine.initialize(const DeepSeekConfig(apiKey: 'test')),
        ASRError.none);
    final p = calloc<Float>(160);
    engine.acceptWaveform(16000, p, 160);
    engine.reset();
    expect((await engine.finalizeUtterance()).text, '');
    engine.dispose();
    calloc.free(p);
  });
}
