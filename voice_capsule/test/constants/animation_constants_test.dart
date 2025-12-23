import 'package:flutter/animation.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:voice_capsule/constants/animation_constants.dart';

void main() {
  group('AnimationConstants Ripple Tests', () {
    test('rippleDuration is 1500ms', () {
      expect(
        AnimationConstants.rippleDuration,
        const Duration(milliseconds: 1500),
      );
    });

    test('rippleCurve is easeOutQuad', () {
      expect(AnimationConstants.rippleCurve, Curves.easeOutQuad);
    });

    test('ripple scale range is 1.0 to 3.0', () {
      expect(AnimationConstants.rippleStartScale, 1.0);
      expect(AnimationConstants.rippleEndScale, 3.0);
    });

    test('ripple opacity range is 0.5 to 0.0', () {
      expect(AnimationConstants.rippleStartOpacity, 0.5);
      expect(AnimationConstants.rippleEndOpacity, 0.0);
    });
  });

  group('AnimationConstants Cursor Tests', () {
    test('cursorDuration is 800ms', () {
      expect(
        AnimationConstants.cursorDuration,
        const Duration(milliseconds: 800),
      );
    });

    test('cursorCurve is easeInOut', () {
      expect(AnimationConstants.cursorCurve, Curves.easeInOut);
    });
  });

  group('AnimationConstants Breathing Tests', () {
    test('breathingBaseScale is 1.0', () {
      expect(AnimationConstants.breathingBaseScale, 1.0);
    });

    test('breathingAmplitude is 0.1', () {
      expect(AnimationConstants.breathingAmplitude, 0.1);
    });

    test('breathingPeriod is 2000ms', () {
      expect(
        AnimationConstants.breathingPeriod,
        const Duration(milliseconds: 2000),
      );
    });

    test('breathing scale range is 1.0 to 1.1 (base to base + amplitude)', () {
      // 使用归一化 sin 公式: 1.0 + amplitude * (1 + sin(t)) / 2
      // 范围 [1.0, 1.1] 符合 AC2 规范
      final minScale = AnimationConstants.breathingBaseScale;
      final maxScale =
          AnimationConstants.breathingBaseScale + AnimationConstants.breathingAmplitude;
      expect(minScale, 1.0);
      expect(maxScale, 1.1);
    });
  });

  group('AnimationConstants Pulse Tests', () {
    test('pulseDuration is 400ms', () {
      expect(
        AnimationConstants.pulseDuration,
        const Duration(milliseconds: 400),
      );
    });

    test('pulseMaxScale is 1.2', () {
      expect(AnimationConstants.pulseMaxScale, 1.2);
    });
  });
}




