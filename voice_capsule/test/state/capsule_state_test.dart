import 'package:flutter_test/flutter_test.dart';
import 'package:voice_capsule/state/capsule_state.dart';
import 'package:voice_capsule/services/fcitx_client.dart';

void main() {
  group('CapsuleState Enum Tests', () {
    test('contains all expected states including new init states', () {
      // Story 3-7: 新增 initializing, downloading, extracting 状态
      expect(CapsuleState.values.length, 7);
      expect(CapsuleState.values, contains(CapsuleState.idle));
      expect(CapsuleState.values, contains(CapsuleState.listening));
      expect(CapsuleState.values, contains(CapsuleState.processing));
      expect(CapsuleState.values, contains(CapsuleState.error));
      expect(CapsuleState.values, contains(CapsuleState.initializing));
      expect(CapsuleState.values, contains(CapsuleState.downloading));
      expect(CapsuleState.values, contains(CapsuleState.extracting));
    });
  });

  group('CapsuleErrorType Enum Tests', () {
    test('contains all expected error types including refined types', () {
      // Story 3-7: 细化错误类型
      expect(CapsuleErrorType.values.length, 11);
      // 音频相关 (细化)
      expect(CapsuleErrorType.values, contains(CapsuleErrorType.audioNoDevice));
      expect(CapsuleErrorType.values, contains(CapsuleErrorType.audioDeviceBusy));
      expect(CapsuleErrorType.values, contains(CapsuleErrorType.audioPermissionDenied));
      expect(CapsuleErrorType.values, contains(CapsuleErrorType.audioDeviceLost));
      expect(CapsuleErrorType.values, contains(CapsuleErrorType.audioInitFailed));
      // 模型相关 (细化)
      expect(CapsuleErrorType.values, contains(CapsuleErrorType.modelNotFound));
      expect(CapsuleErrorType.values, contains(CapsuleErrorType.modelIncomplete));
      expect(CapsuleErrorType.values, contains(CapsuleErrorType.modelCorrupted));
      expect(CapsuleErrorType.values, contains(CapsuleErrorType.modelLoadFailed));
      // 连接相关
      expect(CapsuleErrorType.values, contains(CapsuleErrorType.socketError));
      // 其他
      expect(CapsuleErrorType.values, contains(CapsuleErrorType.unknown));
    });

    test('backward compatibility: old error types still exist', () {
      // 保持向后兼容 (旧类型重命名)
      expect(CapsuleErrorType.values, contains(CapsuleErrorType.audioInitFailed));
    });
  });

  group('CapsuleStateData with FcitxError Tests', () {
    test('error factory accepts fcitxError parameter', () {
      final state = CapsuleStateData.error(
        CapsuleErrorType.socketError,
        fcitxError: FcitxError.socketNotFound,
      );
      expect(state.state, CapsuleState.error);
      expect(state.errorType, CapsuleErrorType.socketError);
      expect(state.fcitxError, FcitxError.socketNotFound);
    });

    test('displayMessage returns correct message for socketNotFound', () {
      final state = CapsuleStateData.error(
        CapsuleErrorType.socketError,
        fcitxError: FcitxError.socketNotFound,
      );
      expect(state.displayMessage, 'Fcitx5 未运行，请先启动输入法');
    });

    test('displayMessage returns correct message for connectionFailed', () {
      final state = CapsuleStateData.error(
        CapsuleErrorType.socketError,
        fcitxError: FcitxError.connectionFailed,
      );
      expect(state.displayMessage, 'Fcitx5 连接失败');
    });

    test('displayMessage returns correct message for sendFailed', () {
      final state = CapsuleStateData.error(
        CapsuleErrorType.socketError,
        fcitxError: FcitxError.sendFailed,
      );
      expect(state.displayMessage, '文本发送失败');
    });

    test('displayMessage returns correct message for reconnectFailed', () {
      final state = CapsuleStateData.error(
        CapsuleErrorType.socketError,
        fcitxError: FcitxError.reconnectFailed,
      );
      expect(state.displayMessage, 'Fcitx5 重连失败，请检查服务状态');
    });

    test('preservedText field stores text for recovery', () {
      final state = CapsuleStateData.error(
        CapsuleErrorType.socketError,
        fcitxError: FcitxError.sendFailed,
        preservedText: '用户说的话',
      );
      expect(state.preservedText, '用户说的话');
    });
  });

  group('CapsuleStateData refined error messages Tests', () {
    test('audioNoDevice returns correct message', () {
      final state = CapsuleStateData.error(CapsuleErrorType.audioNoDevice);
      expect(state.displayMessage, '未检测到麦克风');
    });

    test('audioDeviceBusy returns correct message', () {
      final state = CapsuleStateData.error(CapsuleErrorType.audioDeviceBusy);
      expect(state.displayMessage, '麦克风被其他应用占用');
    });

    test('audioDeviceLost returns correct message', () {
      final state = CapsuleStateData.error(CapsuleErrorType.audioDeviceLost);
      expect(state.displayMessage, '麦克风已断开');
    });

    test('modelNotFound returns correct message', () {
      final state = CapsuleStateData.error(CapsuleErrorType.modelNotFound);
      expect(state.displayMessage, '未找到语音模型');
    });

    test('modelIncomplete returns correct message', () {
      final state = CapsuleStateData.error(CapsuleErrorType.modelIncomplete);
      expect(state.displayMessage, '模型文件不完整');
    });

    test('modelCorrupted returns correct message', () {
      final state = CapsuleStateData.error(CapsuleErrorType.modelCorrupted);
      expect(state.displayMessage, '模型文件损坏');
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
      final state = CapsuleStateData.error(CapsuleErrorType.audioInitFailed);
      expect(state.state, CapsuleState.error);
      expect(state.errorType, CapsuleErrorType.audioInitFailed);
    });

    test('error() creates correct state with custom message', () {
      final state = CapsuleStateData.error(CapsuleErrorType.unknown, message: '自定义错误');
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

    test('returns default error message for audioInitFailed', () {
      final state = CapsuleStateData.error(CapsuleErrorType.audioInitFailed);
      expect(state.displayMessage, '音频设备初始化失败');
    });

    test('returns default error message for modelLoadFailed', () {
      final state = CapsuleStateData.error(CapsuleErrorType.modelLoadFailed);
      expect(state.displayMessage, '模型加载失败');
    });

    test('returns default error message for socketError without fcitxError', () {
      final state = CapsuleStateData.error(CapsuleErrorType.socketError);
      expect(state.displayMessage, 'Fcitx5 连接错误');
    });

    test('returns default error message for unknown error', () {
      final state = CapsuleStateData.error(CapsuleErrorType.unknown);
      expect(state.displayMessage, '未知错误');
    });

    test('returns custom error message when provided', () {
      final state = CapsuleStateData.error(
        CapsuleErrorType.audioInitFailed,
        message: '自定义音频错误',
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
        CapsuleErrorType.modelLoadFailed,
        message: '错误消息',
      );
      final updated = original.copyWith(recognizedText: '测试');
      expect(updated.state, CapsuleState.error);
      expect(updated.errorType, CapsuleErrorType.modelLoadFailed);
      expect(updated.errorMessage, '错误消息');
    });

    test('copyWith preserves fcitxError and preservedText', () {
      final original = CapsuleStateData.error(
        CapsuleErrorType.socketError,
        fcitxError: FcitxError.sendFailed,
        preservedText: '保存的文本',
      );
      final updated = original.copyWith(recognizedText: '测试');
      expect(updated.fcitxError, FcitxError.sendFailed);
      expect(updated.preservedText, '保存的文本');
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





