import 'dart:typed_data';
import 'package:dio/dio.dart';

/// 只暴露可展示的错误码，禁止携带服务端正文、请求头或密钥。
class DeepSeekException implements Exception {
  final String code;
  const DeepSeekException(this.code);
  String message(bool zh) => switch (code) {
        'auth' =>
          zh ? 'API Key 无效，请检查配置' : 'Invalid API key. Check configuration.',
        'permission' =>
          zh ? '余额不足或没有访问权限' : 'Insufficient balance or access denied.',
        'rate' => zh ? '请求过于频繁，请稍后重试' : 'Rate limited. Try again later.',
        'timeout' => zh ? '识别请求超时，请重试' : 'Recognition timed out. Try again.',
        'cancelled' => zh ? '已取消' : 'Cancelled',
        'response' => zh ? '语音服务返回了无效响应' : 'Invalid speech service response.',
        'audio' => zh ? '音频格式或时长超出限制' : 'Unsupported audio format or duration.',
        'server' =>
          zh ? '语音服务暂时不可用' : 'Speech service is temporarily unavailable.',
        _ => zh
            ? '无法连接 DeepSeek，请检查网络'
            : 'Cannot connect to DeepSeek. Check your network.',
      };
  @override
  String toString() => 'DeepSeekException($code)';
}

/// 本地生成 WAV，不落盘；16 kHz、单声道、16 位 PCM。
Uint8List encodePcm16Wav(Float32List samples) {
  final bytes = Uint8List(44 + samples.length * 2);
  final data = ByteData.sublistView(bytes);
  void tag(int offset, String text) =>
      bytes.setRange(offset, offset + text.length, text.codeUnits);
  tag(0, 'RIFF');
  data.setUint32(4, bytes.length - 8, Endian.little);
  tag(8, 'WAVE');
  tag(12, 'fmt ');
  data.setUint32(16, 16, Endian.little);
  data.setUint16(20, 1, Endian.little);
  data.setUint16(22, 1, Endian.little);
  data.setUint32(24, 16000, Endian.little);
  data.setUint32(28, 32000, Endian.little);
  data.setUint16(32, 2, Endian.little);
  data.setUint16(34, 16, Endian.little);
  tag(36, 'data');
  data.setUint32(40, samples.length * 2, Endian.little);
  for (var i = 0; i < samples.length; i++) {
    final sample = samples[i].isFinite ? samples[i].clamp(-1.0, 1.0) : 0.0;
    data.setInt16(44 + i * 2, (sample * (sample < 0 ? 32768 : 32767)).round(),
        Endian.little);
  }
  return bytes;
}

class DeepSeekAsrClient {
  final Dio _dio;
  DeepSeekAsrClient({Dio? dio})
      : _dio = dio ??
            Dio(BaseOptions(connectTimeout: const Duration(seconds: 15)));
  static const endpoint = 'https://api.deepseek.com/v1/tools/asr';

  Future<String> transcribe(Uint8List wav, String apiKey,
      {CancelToken? cancelToken}) async {
    if (apiKey.trim().isEmpty ||
        apiKey.contains('\n') ||
        apiKey.contains('\r')) {
      throw const DeepSeekException('auth');
    }
    if (wav.length > 8 * 1024 * 1024) throw const DeepSeekException('audio');
    try {
      final response = await _dio.post<Object?>(
        endpoint,
        data: FormData.fromMap({
          'file': MultipartFile.fromBytes(wav,
              filename: 'speech.wav', contentType: DioMediaType('audio', 'wav'))
        }),
        options: Options(
            headers: {'Authorization': 'Bearer ${apiKey.trim()}'},
            sendTimeout: const Duration(seconds: 30),
            receiveTimeout: const Duration(seconds: 60),
            followRedirects: false,
            responseType: ResponseType.json),
        cancelToken: cancelToken,
      );
      final body = response.data;
      if (response.statusCode != 200 ||
          body is! Map ||
          body['text'] is! String ||
          body['request_id'] is! String ||
          body['duration_ms'] is! int) {
        throw const DeepSeekException('response');
      }
      return body['text'] as String;
    } on DioException catch (e) {
      final code = switch (e.type) {
        DioExceptionType.cancel => 'cancelled',
        DioExceptionType.connectionTimeout ||
        DioExceptionType.sendTimeout ||
        DioExceptionType.receiveTimeout =>
          'timeout',
        DioExceptionType.badResponse => switch (e.response?.statusCode) {
            401 => 'auth',
            402 || 403 => 'permission',
            429 => 'rate',
            400 || 413 || 422 => 'audio',
            408 || 504 => 'timeout',
            _ => 'server',
          },
        _ => 'network',
      };
      throw DeepSeekException(code);
    } on FormatException {
      throw const DeepSeekException('response');
    }
  }

  Future<void> testConnection(String apiKey, {CancelToken? cancelToken}) async {
    await transcribe(encodePcm16Wav(Float32List(16000)), apiKey,
        cancelToken: cancelToken);
  }

  void close() => _dio.close(force: true);
}
