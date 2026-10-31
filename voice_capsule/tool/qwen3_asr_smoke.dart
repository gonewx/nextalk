import 'dart:ffi';
import 'dart:io';
import 'dart:typed_data';
import 'package:ffi/ffi.dart';
import 'package:voice_capsule/services/asr/asr_engine.dart';
import 'package:voice_capsule/services/asr/qwen3_asr_engine.dart';

/// 用真实模型验证 Dart FFI、VAD 尾段识别和两次发话的状态隔离。
/// 参数：模型目录、silero_vad.onnx 路径、16 kHz 单声道 PCM16 WAV。
Future<void> main(List<String> args) async {
  if (args.length != 3) {
    stderr.writeln('用法：dart run tool/qwen3_asr_smoke.dart 模型目录 VAD文件 WAV文件');
    exitCode = 64;
    return;
  }
  final bytes = await File(args[2]).readAsBytes();
  final data = ByteData.sublistView(bytes);
  if (String.fromCharCodes(bytes.take(4)) != 'RIFF' ||
      String.fromCharCodes(bytes.sublist(8, 12)) != 'WAVE') {
    throw FormatException('需要 RIFF WAV 文件');
  }
  int? audioOffset;
  int? audioLength;
  bool validFormat = false;
  for (var offset = 12; offset + 8 <= bytes.length;) {
    final name = String.fromCharCodes(bytes.sublist(offset, offset + 4));
    final size = data.getUint32(offset + 4, Endian.little);
    if (offset + 8 + size > bytes.length) throw FormatException('WAV 文件被截断');
    if (name == 'fmt ' && size >= 16) {
      validFormat = data.getUint16(offset + 8, Endian.little) == 1 &&
          data.getUint16(offset + 10, Endian.little) == 1 &&
          data.getUint32(offset + 12, Endian.little) == 16000 &&
          data.getUint16(offset + 22, Endian.little) == 16;
    }
    if (name == 'data') {
      audioOffset = offset + 8;
      audioLength = size;
    }
    offset += 8 + size + (size % 2);
  }
  if (!validFormat || audioOffset == null || audioLength == null) {
    throw FormatException('仅支持 16 kHz 单声道 PCM16 WAV');
  }
  final n = audioLength ~/ 2;
  final samples = calloc<Float>(n);
  final engine = Qwen3AsrEngine();
  try {
    for (var i = 0; i < n; i++) {
      samples[i] = data.getInt16(audioOffset + i * 2, Endian.little) / 32768;
    }
    final timer = Stopwatch()..start();
    final error = await engine.initialize(Qwen3AsrConfig(
      modelDir: args[0],
      vadModelPath: args[1],
      numThreads: 2,
    ));
    if (error != ASRError.none) throw StateError('初始化失败：$error');
    stdout.writeln('初始化：${timer.elapsedMilliseconds} ms；音频：${n / 16000} 秒');
    String? previous;
    for (var session = 1; session <= 2; session++) {
      timer.reset();
      // 按实际录音块送入，最后一个不足窗口的块由 finalizeUtterance 刷出。
      for (var offset = 0; offset < n; offset += 512) {
        final count = n - offset < 512 ? n - offset : 512;
        engine.acceptWaveform(16000, samples + offset, count);
      }
      final result = engine.finalizeUtterance();
      stdout.writeln(
          '第 $session 次识别：${timer.elapsedMilliseconds} ms；结果：${result.text}');
      if (result.isEmpty ||
          engine.getResult().isNotEmpty ||
          engine.isEndpoint()) {
        throw StateError('识别为空或会话状态未清空');
      }
      if (previous != null && result.text != previous) {
        throw StateError('重复识别结果不同，需检查会话隔离');
      }
      previous = result.text;
    }
  } finally {
    engine.dispose();
    calloc.free(samples);
  }
}
