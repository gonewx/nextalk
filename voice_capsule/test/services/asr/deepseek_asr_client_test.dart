import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';
import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:voice_capsule/services/asr/deepseek_asr_client.dart';

class TestAdapter implements HttpClientAdapter {
  TestAdapter(this.handler);
  final Future<ResponseBody> Function(RequestOptions, Stream<Uint8List>?)
      handler;
  @override
  Future<ResponseBody> fetch(RequestOptions options,
          Stream<Uint8List>? requestStream, Future<void>? cancelFuture) =>
      handler(options, requestStream);
  @override
  void close({bool force = false}) {}
}

void main() {
  test('sends authenticated multipart WAV and reads transcript', () async {
    final dio = Dio();
    dio.httpClientAdapter = TestAdapter((options, stream) async {
      expect(options.uri.toString(), DeepSeekAsrClient.endpoint);
      expect(options.headers['Authorization'], 'Bearer secret');
      expect(options.followRedirects, false);
      final bytes = await stream!.expand((x) => x).toList();
      final body = latin1.decode(bytes);
      expect(body, contains('name="file"; filename="speech.wav"'));
      expect(body, contains('RIFF'));
      expect(body, contains('WAVE'));
      return ResponseBody.fromString(
          jsonEncode({'text': '你好', 'request_id': 'r', 'duration_ms': 1000}),
          200,
          headers: {
            Headers.contentTypeHeader: ['application/json']
          });
    });
    final client = DeepSeekAsrClient(dio: dio);
    expect(
        await client.transcribe(encodePcm16Wav(Float32List(16000)), 'secret'),
        '你好');
    client.close();
  });
  for (final entry in {
    401: 'auth',
    402: 'permission',
    403: 'permission',
    429: 'rate',
    503: 'server',
    504: 'timeout',
    413: 'audio'
  }.entries) {
    test('HTTP ${entry.key} is sanitized and not retried', () async {
      var calls = 0;
      final dio = Dio()
        ..httpClientAdapter = TestAdapter((_, __) async {
          calls++;
          return ResponseBody.fromString('secret echoed by server', entry.key);
        });
      final client = DeepSeekAsrClient(dio: dio);
      await expectLater(
          client.transcribe(Uint8List(44), 'secret'),
          throwsA(isA<DeepSeekException>()
              .having((e) => e.code, 'code', entry.value)
              .having((e) => e.toString(), 'sanitized',
                  isNot(contains('secret')))));
      expect(calls, 1);
      client.close();
    });
  }
  test('malformed success is rejected', () async {
    final dio = Dio()
      ..httpClientAdapter = TestAdapter((_, __) async =>
          ResponseBody.fromString('{"text": 3}', 200, headers: {
            Headers.contentTypeHeader: ['application/json']
          }));
    final client = DeepSeekAsrClient(dio: dio);
    await expectLater(
        client.transcribe(Uint8List(44), 'secret'),
        throwsA(isA<DeepSeekException>()
            .having((e) => e.code, 'code', 'response')));
    client.close();
  });
  test('connection test accepts empty transcript and uses one second silence',
      () async {
    final dio = Dio()
      ..httpClientAdapter = TestAdapter((options, stream) async {
        final form = options.data as FormData;
        expect(form.files.single.value.length, 32044);
        return ResponseBody.fromString(
            '{"text":"","request_id":"r","duration_ms":1000}', 200,
            headers: {
              Headers.contentTypeHeader: ['application/json']
            });
      });
    final client = DeepSeekAsrClient(dio: dio);
    await client.testConnection('secret');
    client.close();
  });
}
