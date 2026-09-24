import 'package:flutter_test/flutter_test.dart';
import 'package:voice_capsule/services/text_post_processor.dart';

void main() {
  const processor = TextPostProcessor();

  group('TextPostProcessor 大小写', () {
    test('全大写英文转小写，保留 I', () {
      expect(processor.process('I THINK THIS IS GOOD'), 'I think this is good');
      expect(processor.process("I'M FINE"), "I'm fine");
    });

    test('中英混合的全大写英文同样转换', () {
      expect(processor.process('我想用PYTHON写代码'), '我想用python写代码');
    });

    test('已有小写字母时不改动 (SenseVoice 风格输出)', () {
      expect(processor.process('Hello World from NASA'),
          'Hello World from NASA');
    });
  });

  group('TextPostProcessor 填充词', () {
    test('移除句首与标点后的中文填充词', () {
      expect(processor.process('嗯，我们明天开会'), '我们明天开会');
      expect(processor.process('好的。呃，那就这样'), '好的。那就这样');
    });

    test('不误伤正常用字', () {
      expect(processor.process('额外的额度'), '额外的额度');
      expect(processor.process('嗯嗯好的'), '好的');
    });

    test('移除英文填充词', () {
      expect(processor.process('um I think uh we should go'),
          'I think we should go');
    });

    test('整段只有填充词时保留原文', () {
      expect(processor.process('嗯'), '嗯');
    });
  });

  group('TextPostProcessor 重复与标点', () {
    test('合并连续重复的英文单词', () {
      expect(processor.process('this is the the answer'), 'this is the answer');
    });

    test('中文语境下半角标点全角化', () {
      expect(processor.process('你好,世界?'), '你好，世界？');
      expect(processor.process('我用 Python, 很好'), '我用 Python，很好');
    });

    test('英文语境保留半角标点', () {
      expect(processor.process('hello, world'), 'hello, world');
      expect(processor.process('时间 10:30'), '时间 10:30');
    });

    test('去除重复标点与标点前空格', () {
      expect(processor.process('好的，，谢谢 。'), '好的，谢谢。');
    });

    test('合并多余空格', () {
      expect(processor.process('  hello    world  '), 'hello world');
    });
  });

  group('TextPostProcessor 自定义词典', () {
    test('英文按单词边界忽略大小写替换，长词优先', () {
      const p = TextPostProcessor(replacements: {
        'next talk': 'Nextalk',
        'next': 'NEXT',
      });
      expect(p.process('I love next talk'), 'I love Nextalk');
      expect(p.process('next step'), 'NEXT step');
      expect(p.process('nextday'), 'nextday');
    });

    test('中文字面替换', () {
      const p = TextPostProcessor(replacements: {'派森': 'Python'});
      expect(p.process('我在学派森'), '我在学Python');
    });
  });

  group('TextPostProcessor 可选规则', () {
    test('中英文之间加空格', () {
      const p = TextPostProcessor(cjkSpacing: true);
      expect(p.process('用Python写3个脚本'), '用 Python 写 3 个脚本');
    });

    test('去掉末尾句号', () {
      const p = TextPostProcessor(stripTrailingPeriod: true);
      expect(p.process('今天天气不错。'), '今天天气不错');
    });

    test('总开关关闭时原样返回', () {
      expect(TextPostProcessor.disabled.process('嗯，HELLO'), '嗯，HELLO');
    });
  });

  group('TextPostProcessor.fromConfig', () {
    test('null 配置使用默认值', () {
      final p = TextPostProcessor.fromConfig(null);
      expect(p.enabled, isTrue);
      expect(p.cjkSpacing, isFalse);
    });

    test('解析开关与替换词典，忽略非法项', () {
      final p = TextPostProcessor.fromConfig({
        'auto_correct': true,
        'cjk_spacing': true,
        'remove_fillers': 'yes', // 非 bool 使用默认值
        'replacements': {'get hub': 'GitHub', '': 'x', 'empty': null},
      });
      expect(p.cjkSpacing, isTrue);
      expect(p.removeFillers, isTrue);
      expect(p.replacements, {'get hub': 'GitHub'});
    });

    test('replacements 为空节 (YAML null) 时不报错', () {
      final p = TextPostProcessor.fromConfig({'replacements': null});
      expect(p.replacements, isEmpty);
    });
  });
}
