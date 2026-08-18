import 'package:flutter_test/flutter_test.dart';
import 'package:voice_capsule/main.dart';

/// 冷启动意图决策测试。
///
/// 守的是什么: 无实例运行时按快捷键, nextalk-toggle 会回退到 `nextalk --toggle`
/// 冷启动。若这一路径不把用户的原始意图记下来待就绪后补执行, 应用就只是被静默
/// 拉起 —— 窗口不显示、录音不开始 (WindowService 以 showOnStartup: false 初始化),
/// 用户必须再按一次才有反应, 观感是"第一次按键丢了"。
void main() {
  group('decideCommandAction', () {
    test('已有实例接手时本进程只当信使并退出', () {
      for (final cmd in ['--toggle', '--show', '--hide']) {
        final d = decideCommandAction(cmd, commandSent: true);
        expect(d.shouldContinue, isFalse, reason: '$cmd 已送达, 不该再启动一个实例');
        expect(d.pendingCommand, isNull,
            reason: '$cmd 已由运行中的实例执行, 本进程无需补做');
      }
    });

    test('无实例时 --toggle 冷启动并记下意图', () {
      final d = decideCommandAction('--toggle', commandSent: false);
      expect(d.shouldContinue, isTrue);
      expect(d.pendingCommand, 'toggle',
          reason: '不记意图, 用户这一次按键就白按了');
    });

    test('无实例时 --show 冷启动并记下意图', () {
      final d = decideCommandAction('--show', commandSent: false);
      expect(d.shouldContinue, isTrue);
      expect(d.pendingCommand, 'show');
    });

    test('无实例时 --hide 无事可做, 不拉起应用', () {
      final d = decideCommandAction('--hide', commandSent: false);
      expect(d.shouldContinue, isFalse,
          reason: '没有窗口可隐藏, 为此启动整个应用是纯粹的浪费');
      expect(d.pendingCommand, isNull);
    });

    test('pendingCommand 去掉了 -- 前缀, 与 socket 命令名一致', () {
      // 补执行走 HotkeyController, 命令名必须与 SingleInstance.onCommand
      // 收到的字符串同形, 否则两条路径行为分叉
      expect(decideCommandAction('--toggle', commandSent: false).pendingCommand,
          isNot(startsWith('-')));
      expect(decideCommandAction('--show', commandSent: false).pendingCommand,
          isNot(startsWith('-')));
    });
  });
}
