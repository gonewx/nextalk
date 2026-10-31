import 'dart:io';

/// 官方 2026-03-25 int8 模型包的文件布局，不使用 tokens.txt。
class Qwen3AsrConstants {
  Qwen3AsrConstants._();
  static const convFrontend = 'conv_frontend.onnx';
  static const encoder = 'encoder.int8.onnx';
  static const decoder = 'decoder.int8.onnx';
  static const tokenizer = 'tokenizer';
  static const requiredFiles = [
    convFrontend,
    encoder,
    decoder,
    'tokenizer/vocab.json',
    'tokenizer/merges.txt',
    'tokenizer/tokenizer_config.json',
  ];

  /// 下载另做 SHA256 校验；此检查用于启动和手动安装时确认文件完整。
  static bool hasRequiredFiles(String modelDir) {
    try {
      return requiredFiles.every((name) {
        final file = File('$modelDir/$name');
        return file.existsSync() && file.lengthSync() > 0;
      });
    } on FileSystemException {
      return false;
    }
  }
}
