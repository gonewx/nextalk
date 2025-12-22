import 'package:flutter_test/flutter_test.dart';
import 'package:voice_capsule/state/capsule_state.dart';

void main() {
  group('CapsuleState Enum Tests', () {
    test('contains all expected states', () {
      expect(CapsuleState.values.length, 4);
      expect(CapsuleState.values, contains(CapsuleState.idle));
      expect(CapsuleState.values, contains(CapsuleState.listening));
      expect(CapsuleState.values, contains(CapsuleState.processing));
      expect(CapsuleState.values, contains(CapsuleState.error));
    });
  });

  group('CapsuleErrorType Enum Tests', () {
    test('contains all expected error types', () {
      expect(CapsuleErrorType.values.length, 4);
      expect(CapsuleErrorType.values, contains(CapsuleErrorType.audioDeviceError));
      expect(CapsuleErrorType.values, contains(CapsuleErrorType.modelError));
      expect(CapsuleErrorType.values, contains(CapsuleErrorType.socketDisconnected));
      expect(CapsuleErrorType.values, contains(CapsuleErrorType.unknown));
    });
  });

  group('CapsuleStateData Factory Tests', () {
    test('idle() creates correct state', () {
      final state = CapsuleStateData.idle();
      expect(state.state, CapsuleState.idle);
      expect(state.errorType, isNull);
      expect(state.recognizedText, '');
    });

    test('idle() creates correct state with text', () {
      final state = CapsuleStateData.idle(text: '空闲文本');
      expect(state.state, CapsuleState.idle);
      expect(state.recognizedText, '空闲文本');
    });

    test('listening() creates correct state with text', () {
      final state = CapsuleStateData.listening(text: '你好');
      expect(state.state, CapsuleState.listening);
      expect(state.recognizedText, '你好');
      expect(state.displayMessage, '你好');
    });

    test('listening() creates correct state without text', () {
      final state = CapsuleStateData.listening();
      expect(state.state, CapsuleState.listening);
      expect(state.recognizedText, '');
    });

    test('processing() creates correct state with text', () {
      final state = CapsuleStateData.processing(text: '处理中');
      expect(state.state, CapsuleState.processing);
      expect(state.recognizedText, '处理中');
      expect(state.displayMessage, '处理中');
    });

    test('error() creates correct state with type', () {
      final state = CapsuleStateData.error(CapsuleErrorType.audioDeviceError);
      expect(state.state, CapsuleState.error);
      expect(state.errorType, CapsuleErrorType.audioDeviceError);
    });

    test('error() creates correct state with custom message', () {
      final state = CapsuleStateData.error(CapsuleErrorType.unknown, '自定义错误');
      expect(state.state, CapsuleState.error);
      expect(state.errorMessage, '自定义错误');
      expect(state.displayMessage, '自定义错误');
    });
  });

  group('CapsuleStateData displayMessage Tests', () {
    test('returns recognized text for listening state', () {
      final state = CapsuleStateData.listening(text: '测试文本');
      expect(state.displayMessage, '测试文本');
    });

    test('returns recognized text for processing state', () {
      final state = CapsuleStateData.processing(text: '处理文本');
      expect(state.displayMessage, '处理文本');
    });

    test('returns default error message for audioDeviceError', () {
      final state = CapsuleStateData.error(CapsuleErrorType.audioDeviceError);
      expect(state.displayMessage, '音频设备异常');
    });

    test('returns default error message for modelError', () {
      final state = CapsuleStateData.error(CapsuleErrorType.modelError);
      expect(state.displayMessage, '模型损坏，请重启');
    });

    test('returns default error message for socketDisconnected', () {
      final state = CapsuleStateData.error(CapsuleErrorType.socketDisconnected);
      expect(state.displayMessage, 'Fcitx5 未连接');
    });

    test('returns default error message for unknown error', () {
      final state = CapsuleStateData.error(CapsuleErrorType.unknown);
      expect(state.displayMessage, '未知错误');
    });

    test('returns custom error message when provided', () {
      final state = CapsuleStateData.error(
        CapsuleErrorType.audioDeviceError,
        '自定义音频错误',
      );
      expect(state.displayMessage, '自定义音频错误');
    });
  });

  group('CapsuleStateData equality Tests', () {
    test('identical states are equal', () {
      final state1 = CapsuleStateData.listening(text: '你好');
      final state2 = CapsuleStateData.listening(text: '你好');
      expect(state1, equals(state2));
      expect(state1.hashCode, equals(state2.hashCode));
    });

    test('different states are not equal', () {
      final state1 = CapsuleStateData.listening(text: '你好');
      final state2 = CapsuleStateData.processing(text: '你好');
      expect(state1, isNot(equals(state2)));
    });

    test('different texts make states not equal', () {
      final state1 = CapsuleStateData.listening(text: '你好');
      final state2 = CapsuleStateData.listening(text: '世界');
      expect(state1, isNot(equals(state2)));
    });
  });

  group('CapsuleStateData copyWith Tests', () {
    test('copyWith updates state', () {
      final original = CapsuleStateData.listening(text: '你好');
      final updated = original.copyWith(state: CapsuleState.processing);
      expect(updated.state, CapsuleState.processing);
      expect(updated.recognizedText, '你好');
    });

    test('copyWith updates text', () {
      final original = CapsuleStateData.listening(text: '你好');
      final updated = original.copyWith(recognizedText: '世界');
      expect(updated.state, CapsuleState.listening);
      expect(updated.recognizedText, '世界');
    });

    test('copyWith preserves unchanged fields', () {
      final original = CapsuleStateData.error(
        CapsuleErrorType.modelError,
        '错误消息',
      );
      final updated = original.copyWith(recognizedText: '测试');
      expect(updated.state, CapsuleState.error);
      expect(updated.errorType, CapsuleErrorType.modelError);
      expect(updated.errorMessage, '错误消息');
    });
  });

  group('CapsuleStateData toString Tests', () {
    test('toString returns readable format', () {
      final state = CapsuleStateData.listening(text: '你好');
      expect(
        state.toString(),
        'CapsuleStateData(state: CapsuleState.listening, errorType: null, text: 你好)',
      );
    });
  });
}
