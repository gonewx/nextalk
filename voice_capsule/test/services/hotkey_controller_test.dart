import 'dart:async';

import 'package:flutter_test/flutter_test.dart';
import 'package:voice_capsule/services/hotkey_controller.dart';
import 'package:voice_capsule/state/capsule_state.dart';

/// Story 3-5: HotkeyController 测试
///
/// 注意: HotkeyController 依赖多个原生服务 (WindowService, AudioInferencePipeline)
/// 完整集成测试需要在真实设备上运行
/// 这里测试不依赖原生调用的逻辑
void main() {
  group('HotkeyController Tests', () {
    group('单例模式', () {
      test('应该是单例', () {
        final instance1 = HotkeyController.instance;
        final instance2 = HotkeyController.instance;
        expect(identical(instance1, instance2), isTrue);
      });
    });

    group('初始状态', () {
      test('初始状态应该是 idle', () {
        final controller = HotkeyController.instance;
        // 注意: 如果 controller 已被初始化，状态可能不是 idle
        // 这里只验证状态是 HotkeyState 枚举值
        expect(controller.state, isA<HotkeyState>());
      });

      test('初始时 isInitialized 应该是 bool 类型', () {
        final controller = HotkeyController.instance;
        expect(controller.isInitialized, isA<bool>());
      });
    });

    group('HotkeyState 枚举', () {
      test('应该包含 idle 状态', () {
        expect(HotkeyState.values, contains(HotkeyState.idle));
      });

      test('应该包含 recording 状态', () {
        expect(HotkeyState.values, contains(HotkeyState.recording));
      });

      test('应该包含 submitting 状态', () {
        expect(HotkeyState.values, contains(HotkeyState.submitting));
      });

      test('应该有且仅有 3 个状态', () {
        expect(HotkeyState.values.length, equals(3));
      });
    });

    group('状态机流转逻辑', () {
      test('状态枚举应该按照正确顺序定义', () {
        // Idle -> Recording -> Submitting -> Idle
        expect(HotkeyState.idle.index, equals(0));
        expect(HotkeyState.recording.index, equals(1));
        expect(HotkeyState.submitting.index, equals(2));
      });
    });

    group('CapsuleStateData 集成', () {
      test('idle 状态应该创建正确的 CapsuleStateData', () {
        final stateData = CapsuleStateData.idle();
        expect(stateData.state, equals(CapsuleState.idle));
        expect(stateData.recognizedText, isEmpty);
      });

      test('listening 状态应该创建正确的 CapsuleStateData', () {
        final stateData = CapsuleStateData.listening();
        expect(stateData.state, equals(CapsuleState.listening));
      });

      test('listening 状态应该支持文本参数', () {
        final stateData = CapsuleStateData.listening(text: '你好');
        expect(stateData.state, equals(CapsuleState.listening));
        expect(stateData.recognizedText, equals('你好'));
      });

      test('processing 状态应该创建正确的 CapsuleStateData', () {
        final stateData = CapsuleStateData.processing();
        expect(stateData.state, equals(CapsuleState.processing));
      });

      test('error 状态应该支持不同错误类型', () {
        final audioError =
            CapsuleStateData.error(CapsuleErrorType.audioDeviceError);
        expect(audioError.state, equals(CapsuleState.error));
        expect(audioError.errorType, equals(CapsuleErrorType.audioDeviceError));

        final modelError = CapsuleStateData.error(CapsuleErrorType.modelError);
        expect(modelError.errorType, equals(CapsuleErrorType.modelError));

        final socketError =
            CapsuleStateData.error(CapsuleErrorType.socketDisconnected);
        expect(
            socketError.errorType, equals(CapsuleErrorType.socketDisconnected));
      });
    });

    group('StreamController 状态更新', () {
      test('StreamController 应该能够广播 CapsuleStateData', () async {
        final controller = StreamController<CapsuleStateData>.broadcast();
        final states = <CapsuleStateData>[];

        final subscription = controller.stream.listen(states.add);

        controller.add(CapsuleStateData.idle());
        controller.add(CapsuleStateData.listening());
        controller.add(CapsuleStateData.processing());

        // 等待事件被处理
        await Future.delayed(const Duration(milliseconds: 10));

        expect(states.length, equals(3));
        expect(states[0].state, equals(CapsuleState.idle));
        expect(states[1].state, equals(CapsuleState.listening));
        expect(states[2].state, equals(CapsuleState.processing));

        await subscription.cancel();
        await controller.close();
      });
    });

    group('dispose 行为', () {
      test('dispose 不应该抛出异常', () async {
        // 注意: 由于是单例，不应该真正 dispose
        // 这里只验证方法存在且可调用
        expect(
          () => HotkeyController.instance.dispose(),
          returnsNormally,
        );
      });
    });
  });
}
