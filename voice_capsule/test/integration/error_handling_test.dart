import 'package:flutter_test/flutter_test.dart';
import 'package:voice_capsule/state/capsule_state.dart';
import 'package:voice_capsule/state/init_state.dart';
import 'package:voice_capsule/services/model_manager.dart';

/// Story 3-7: 错误处理集成测试
/// 验证各种错误场景的状态转换和用户交互流程
void main() {
  group('Error State Transitions (AC8-AC10)', () {
    test('CapsuleStateData.error creates correct state for model errors', () {
      final state = CapsuleStateData.error(CapsuleErrorType.modelNotFound);
      expect(state.state, CapsuleState.error);
      expect(state.errorType, CapsuleErrorType.modelNotFound);
      expect(state.displayMessage, contains('未找到'));
    });

    test('CapsuleStateData.error creates correct state for incomplete model',
        () {
      final state = CapsuleStateData.error(CapsuleErrorType.modelIncomplete);
      expect(state.state, CapsuleState.error);
      expect(state.errorType, CapsuleErrorType.modelIncomplete);
    });

    test('CapsuleStateData.error creates correct state for load failure', () {
      final state = CapsuleStateData.error(CapsuleErrorType.modelLoadFailed);
      expect(state.state, CapsuleState.error);
      expect(state.errorType, CapsuleErrorType.modelLoadFailed);
    });
  });

  group('Audio Error Handling (AC11-AC13)', () {
    test('CapsuleStateData.error creates correct state for no device', () {
      final state = CapsuleStateData.error(CapsuleErrorType.audioNoDevice);
      expect(state.state, CapsuleState.error);
      expect(state.errorType, CapsuleErrorType.audioNoDevice);
      expect(state.displayMessage, contains('未检测到'));
    });

    test('CapsuleStateData.error creates correct state for device busy', () {
      final state = CapsuleStateData.error(CapsuleErrorType.audioDeviceBusy);
      expect(state.state, CapsuleState.error);
      expect(state.errorType, CapsuleErrorType.audioDeviceBusy);
    });

    test(
        'CapsuleStateData.error creates correct state for device lost with preserved text',
        () {
      final state = CapsuleStateData.error(
        CapsuleErrorType.audioDeviceLost,
        preservedText: '这是用户说的话',
      );
      expect(state.state, CapsuleState.error);
      expect(state.errorType, CapsuleErrorType.audioDeviceLost);
      expect(state.preservedText, '这是用户说的话');
    });
  });

  group('Socket Error Handling (AC14-AC15)', () {
    test('CapsuleStateData.error creates correct state for socket error', () {
      final state = CapsuleStateData.error(CapsuleErrorType.socketError);
      expect(state.state, CapsuleState.error);
      expect(state.errorType, CapsuleErrorType.socketError);
    });

    test('Socket error preserves text for retry', () {
      final state = CapsuleStateData.error(
        CapsuleErrorType.socketError,
        preservedText: '保护的文本',
      );
      expect(state.preservedText, '保护的文本');
    });
  });

  group('Init State Error Handling (AC1-AC7)', () {
    test('InitStateData.error creates correct state for network error', () {
      final state = InitStateData.error(ModelError.networkError);
      expect(state.phase, InitPhase.error);
      expect(state.modelError, ModelError.networkError);
      expect(state.canRetry, true);
    });

    test('InitStateData.error creates correct state for disk space error', () {
      final state = InitStateData.error(ModelError.diskSpaceError);
      expect(state.phase, InitPhase.error);
      expect(state.canRetry, true);
    });

    test('InitStateData.error creates correct state for checksum mismatch', () {
      final state = InitStateData.error(ModelError.checksumMismatch);
      expect(state.phase, InitPhase.error);
      expect(state.canRetry, true);
    });

    test('InitStateData.error creates correct state for permission denied', () {
      final state = InitStateData.error(ModelError.permissionDenied);
      expect(state.phase, InitPhase.error);
      expect(state.canRetry, false); // Cannot retry permission errors
    });
  });

  group('Global Error Boundary (AC17-AC18)', () {
    test('CapsuleErrorType has all expected error types', () {
      expect(CapsuleErrorType.values, contains(CapsuleErrorType.audioNoDevice));
      expect(
          CapsuleErrorType.values, contains(CapsuleErrorType.audioDeviceBusy));
      expect(
          CapsuleErrorType.values, contains(CapsuleErrorType.audioDeviceLost));
      expect(
          CapsuleErrorType.values, contains(CapsuleErrorType.audioInitFailed));
      expect(CapsuleErrorType.values, contains(CapsuleErrorType.modelNotFound));
      expect(
          CapsuleErrorType.values, contains(CapsuleErrorType.modelIncomplete));
      expect(
          CapsuleErrorType.values, contains(CapsuleErrorType.modelLoadFailed));
      expect(CapsuleErrorType.values, contains(CapsuleErrorType.socketError));
      expect(CapsuleErrorType.values, contains(CapsuleErrorType.unknown));
    });

    test('ModelError has all expected error types', () {
      expect(ModelError.values, contains(ModelError.none));
      expect(ModelError.values, contains(ModelError.networkError));
      expect(ModelError.values, contains(ModelError.diskSpaceError));
      expect(ModelError.values, contains(ModelError.checksumMismatch));
      expect(ModelError.values, contains(ModelError.extractionFailed));
      expect(ModelError.values, contains(ModelError.permissionDenied));
      expect(ModelError.values, contains(ModelError.downloadCancelled));
    });
  });

  group('Error Message Localization', () {
    test('CapsuleStateData provides correct Chinese error messages', () {
      expect(
        CapsuleStateData.error(CapsuleErrorType.audioNoDevice).displayMessage,
        contains('麦克风'),
      );
      expect(
        CapsuleStateData.error(CapsuleErrorType.socketError).displayMessage,
        contains('Fcitx5'),
      );
    });

    test('InitStateData provides correct Chinese error messages', () {
      expect(
        InitStateData.error(ModelError.networkError).errorMessage,
        contains('网络'),
      );
      expect(
        InitStateData.error(ModelError.diskSpaceError).errorMessage,
        contains('磁盘'),
      );
    });
  });
}
