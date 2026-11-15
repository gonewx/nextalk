import 'dart:async';
import 'dart:ffi';
import 'dart:typed_data';
import 'package:dio/dio.dart';
import 'package:ffi/ffi.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:voice_capsule/services/asr/asr_engine.dart';
import 'package:voice_capsule/services/asr/deepseek_asr_client.dart';
import 'package:voice_capsule/services/asr/deepseek_asr_engine.dart';
import 'package:voice_capsule/services/audio_capture.dart';
import 'package:voice_capsule/services/audio_inference_pipeline.dart';
import 'package:voice_capsule/services/model_manager.dart';

class Capture extends AudioCapture {
  final data = calloc<Float>(1600);
  bool stopped = true;
  @override
  Pointer<Float> get buffer => data;
  @override
  Future<AudioCaptureError> start({String? deviceName}) async {
    stopped = false;
    return AudioCaptureError.none;
  }

  @override
  Future<int> readAsync(Pointer<Float> buffer, int samples) async => 1600;
  @override
  Future<void> stop() async {
    stopped = true;
  }

  @override
  void dispose() {
    calloc.free(data);
  }
}

class PendingClient extends DeepSeekAsrClient {
  PendingClient(this.capture);
  final Capture capture;
  int calls = 0;
  final sent = Completer<void>();
  Completer<String>? response;
  @override
  Future<String> transcribe(Uint8List wav, String apiKey,
      {CancelToken? cancelToken}) {
    expect(capture.stopped, true, reason: 'microphone released before HTTP');
    calls++;
    response = Completer<String>();
    if (!sent.isCompleted) sent.complete();
    final pending = response!;
    cancelToken?.whenCancel.then((_) {
      if (!pending.isCompleted) {
        pending.completeError(const DeepSeekException('cancelled'));
      }
    });
    return pending.future;
  }
}

class ConfiguredEngine extends DeepSeekAsrEngine {
  ConfiguredEngine(PendingClient client) : super(client: client);
  @override
  Future<ASRError> initialize(ASRConfig config) =>
      super.initialize(const DeepSeekConfig(apiKey: 'test'));
}

void main() {
  test(
      'cloud stop releases microphone, returns transcript and permits next recording',
      () async {
    final capture = Capture();
    final client = PendingClient(capture);
    final pipeline = AudioInferencePipeline(
        audioCapture: capture,
        asrEngine: ConfiguredEngine(client),
        modelManager: ModelManager());
    expect(await pipeline.start(), PipelineError.none);
    final stopping = pipeline.stop();
    await client.sent.future;
    client.response!.complete('完整句子');
    expect(await stopping, '完整句子');
    expect(pipeline.state, PipelineState.idle);
    expect(await pipeline.start(), PipelineError.none);
    await pipeline.cancel();
    expect(client.calls, 1);
    await pipeline.dispose();
  });
  test('cancel recording never uploads', () async {
    final capture = Capture();
    final client = PendingClient(capture);
    final pipeline = AudioInferencePipeline(
        audioCapture: capture,
        asrEngine: ConfiguredEngine(client),
        modelManager: ModelManager());
    await pipeline.start();
    await pipeline.cancel();
    expect(client.calls, 0);
    expect(capture.stopped, true);
    await pipeline.dispose();
  });
  test('cancel pending request restores pipeline and isolates next recording',
      () async {
    final capture = Capture();
    final client = PendingClient(capture);
    final pipeline = AudioInferencePipeline(
        audioCapture: capture,
        asrEngine: ConfiguredEngine(client),
        modelManager: ModelManager());
    await pipeline.start();
    final stopping = pipeline.stop();
    final assertion = expectLater(stopping, throwsA(isA<DeepSeekException>()));
    await client.sent.future;
    await pipeline.cancel();
    await assertion;
    expect(pipeline.state, PipelineState.idle);
    await pipeline.start();
    expect(pipeline.state, PipelineState.running);
    await pipeline.cancel();
    await pipeline.dispose();
  });
}
