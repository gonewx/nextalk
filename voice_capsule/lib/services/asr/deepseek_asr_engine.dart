import 'dart:ffi';
import 'dart:typed_data';
import 'package:dio/dio.dart';
import 'asr_engine.dart';
import 'deepseek_asr_client.dart';

class DeepSeekAsrEngine extends ASREngine {
  DeepSeekAsrEngine({DeepSeekAsrClient? client})
      : _client = client ?? DeepSeekAsrClient();
  final DeepSeekAsrClient _client;
  static const maxSamples = 16000 * 120;
  Float32List _samples = Float32List(maxSamples);
  int _length = 0;
  int _generation = 0;
  String _apiKey = '';
  CancelToken? _request;
  bool _disposed = false;
  @override
  bool isInitialized = false;
  @override
  ASRError lastError = ASRError.none;
  @override
  ASREngineType get engineType => ASREngineType.deepseek;
  bool get atDurationLimit => _length >= maxSamples;

  @override
  Future<ASRError> initialize(ASRConfig config) async {
    if (_disposed ||
        config is! DeepSeekConfig ||
        config.apiKey.trim().isEmpty) {
      return lastError = ASRError.invalidConfig;
    }
    _apiKey = config.apiKey.trim();
    isInitialized = true;
    return lastError = ASRError.none;
  }

  @override
  void acceptWaveform(int sampleRate, Pointer<Float> samples, int n) {
    if (!isInitialized || _disposed) return;
    if (sampleRate != 16000 || n < 0) throw const DeepSeekException('audio');
    final count = n.clamp(0, maxSamples - _length);
    _samples.setRange(_length, _length + count, samples.asTypedList(count));
    _length += count;
  }

  @override
  Future<ASRResult> finalizeUtterance() async {
    if (_length == 0 || _disposed) return ASRResult.empty();
    final wav = encodePcm16Wav(Float32List.sublistView(_samples, 0, _length));
    _length = 0;
    final generation = ++_generation;
    _request?.cancel();
    final token = _request = CancelToken();
    try {
      final text = await _client.transcribe(wav, _apiKey, cancelToken: token);
      if (_disposed || generation != _generation || token.isCancelled) {
        return ASRResult.empty();
      }
      return ASRResult(text: text);
    } finally {
      if (generation == _generation) _request = null;
    }
  }

  @override
  void reset() {
    _generation++;
    _request?.cancel();
    _request = null;
    _length = 0;
  }

  @override
  void dispose() {
    reset();
    _disposed = true;
    isInitialized = false;
    _apiKey = '';
    _samples = Float32List(0);
    _client.close();
  }

  @override
  bool ensureStreamReady() => isInitialized && !_disposed;
  @override
  ASRResult getResult() => ASRResult.empty();
  @override
  bool isEndpoint() => false;
  @override
  bool isReady() => false;
  @override
  void decode() {}
  @override
  void inputFinished() {}
}
