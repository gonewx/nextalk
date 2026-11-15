import 'dart:async';
import 'dart:ffi';
import 'package:flutter_test/flutter_test.dart';
import 'package:voice_capsule/services/asr/asr_engine.dart';
import 'package:voice_capsule/services/audio_inference_pipeline.dart';
import '../audio_inference_pipeline_test.dart'
    show MockAudioCapture, MockASREngine, MockModelManager;

// 停止时仍有 700ms 音频，最后一块包含可辨识标记。
class BackloggedCapture extends MockAudioCapture {
  int remaining = 0;
  int? reportedFrames = 11200;
  int reads = 0;
  bool failRead = false;
  Completer<void>? readGate;
  final readEntered = Completer<void>();
  bool reading = false;
  bool overlapped = false;
  @override
  Future<int?> pendingFrames() async => reportedFrames;
  @override
  Future<int> readAsync(Pointer<Float> buffer, int samples) async {
    if (reading) overlapped = true;
    reading = true;
    if (!readEntered.isCompleted) readEntered.complete();
    await readGate?.future;
    reading = false;
    if (failRead) return -1;
    buffer.asTypedList(samples).fillRange(0, samples, 0);
    if (remaining > 0) {
      reads++;
      remaining -= samples;
      if (remaining <= 0) buffer[0] = 0.75;
    }
    return samples;
  }
}

class TailEngine extends MockASREngine {
  bool receivedTail = false;
  @override
  void acceptWaveform(int rate, Pointer<Float> samples, int n) {
    if (n > 0 && samples[0] == 0.75) receivedTail = true;
  }

  @override
  ASRResult finalizeUtterance() =>
      ASRResult(text: receivedTail ? '包含尾字' : '缺少尾字');
}

void main() {
  for (final type in ASREngineType.values) {
    test('$type 停止时读取超过 300ms 的积压，保留最后一块音频', () async {
      final capture = BackloggedCapture();
      final engine = TailEngine()..setEngineType(type);
      final pipeline = AudioInferencePipeline(
          audioCapture: capture,
          asrEngine: engine,
          modelManager: MockModelManager());
      addTearDown(pipeline.dispose);
      expect(await pipeline.start(), PipelineError.none);
      capture.remaining = 11200;
      expect(await pipeline.stop(), '包含尾字');
      expect(capture.reads, 7);
    });
  }
  test('非整块积压完整读取，最后一块不越过停止快照', () async {
    final capture = BackloggedCapture()..reportedFrames = 11201;
    final pipeline = AudioInferencePipeline(
        audioCapture: capture,
        asrEngine: TailEngine(),
        modelManager: MockModelManager());
    addTearDown(pipeline.dispose);
    await pipeline.start();
    capture.remaining = 11201;
    expect(await pipeline.stop(), '包含尾字');
    expect(capture.remaining, 0);
  });

  test('在飞读取超过 300ms 时，收尾不能并发读取同一缓冲区', () async {
    final gate = Completer<void>();
    final capture = BackloggedCapture()..readGate = gate;
    final pipeline = AudioInferencePipeline(
        audioCapture: capture,
        asrEngine: TailEngine(),
        modelManager: MockModelManager());
    addTearDown(pipeline.dispose);
    await pipeline.start();
    await capture.readEntered.future;
    final stopping = pipeline.stop();
    await Future<void>.delayed(const Duration(milliseconds: 350));
    // 先解除阻塞再断言，失败时也能释放管线资源。
    gate.complete();
    await stopping;
    expect(capture.overlapped, false);
  });

  test('无法查询积压时仍保留最小尾音读取', () async {
    final capture = BackloggedCapture()..reportedFrames = null;
    final pipeline = AudioInferencePipeline(
        audioCapture: capture,
        asrEngine: TailEngine(),
        modelManager: MockModelManager());
    addTearDown(pipeline.dispose);
    await pipeline.start();
    capture.remaining = 4800;
    expect(await pipeline.stop(), '包含尾字');
  });
  test('尾音读取失败时结束收尾，不无限重试', () async {
    final capture = BackloggedCapture();
    final pipeline = AudioInferencePipeline(
        audioCapture: capture,
        asrEngine: TailEngine(),
        modelManager: MockModelManager());
    addTearDown(pipeline.dispose);
    await pipeline.start();
    capture.failRead = true;
    expect(await pipeline.stop(), '缺少尾字');
    expect(pipeline.state, PipelineState.idle);
  });
}
