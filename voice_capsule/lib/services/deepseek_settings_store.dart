import 'dart:convert';
import 'dart:io';
import 'package:yaml/yaml.dart';

/// 在 YAML 节点范围内修改配置，保留其余配置与注释。
class DeepSeekSettingsStore {
  static String update(String source, String apiKey) {
    final key = apiKey.trim();
    if (key.isEmpty || key.contains('\n') || key.contains('\r')) {
      throw const FormatException('Invalid API key');
    }
    final root = loadYamlNode(source);
    if (root is! YamlMap) {
      throw const FormatException('Settings must be a mapping');
    }
    String replaceNode(YamlNode node, Object value) {
      final suffix = source.substring(node.span.end.offset);
      final encoded = jsonEncode(value);
      // block map 的 span 包含换行；替换后恢复与后继节点的行界。
      final separator =
          node.span.text.endsWith('\n') && !suffix.startsWith('\n') ? '\n' : '';
      return source.replaceRange(
          node.span.start.offset, node.span.end.offset, '$encoded$separator');
    }

    final model = root.nodes['model'];
    String updated;
    if (model == null || model.value == null) {
      final values = Map<String, dynamic>.from(root)
        ..['model'] = {
          'deepseek': {'api_key': key}
        };
      updated = replaceNode(root, values);
    } else {
      if (model is! YamlMap) {
        throw const FormatException('model must be a mapping');
      }
      final deepseek = model.nodes['deepseek'];
      if (deepseek is YamlMap) {
        final node = deepseek.nodes['api_key'];
        if (node != null) {
          updated = replaceNode(node, key);
        } else {
          updated = replaceNode(
              deepseek, Map<String, dynamic>.from(deepseek)..['api_key'] = key);
        }
      } else {
        if (deepseek != null && deepseek.value != null) {
          throw const FormatException('deepseek must be a mapping');
        }
        updated = replaceNode(model,
            Map<String, dynamic>.from(model)..['deepseek'] = {'api_key': key});
      }
    }
    // 先验证再覆盖文件：拒绝重复键、无效结构或丢失密钥的更新。
    final checked = loadYaml(updated);
    if (checked is! YamlMap || checked['model']['deepseek']['api_key'] != key) {
      throw const FormatException('Invalid updated settings');
    }
    return updated;
  }

  static Future<void> saveEngine(File file, String engine) async {
    final source = await file.readAsString();
    final root = loadYamlNode(source);
    if (root is! YamlMap) {
      throw const FormatException('Settings must be a mapping');
    }
    final model = root.nodes['model'];
    final engineNode = model is YamlMap ? model.nodes['engine'] : null;
    String updated;
    if (engineNode != null) {
      updated = source.replaceRange(engineNode.span.start.offset,
          engineNode.span.end.offset, jsonEncode(engine));
    } else {
      final values = Map<String, dynamic>.from(root);
      values['model'] = {
        ...?((model is YamlMap) ? Map<String, dynamic>.from(model) : null),
        'engine': engine
      };
      updated = jsonEncode(values);
    }
    loadYaml(updated);
    await _write(file, updated);
  }

  static Future<void> save(File file, String apiKey) async {
    final source = await file.exists() ? await file.readAsString() : '{}';
    final updated = update(source, apiKey);
    await _write(file, updated);
  }

  static Future<void> _write(File file, String updated) async {
    // 先在私有临时目录创建文件，确保写密钥之前就有访问保护。
    final dir = await file.parent.createTemp('.deepseek-');
    try {
      final temp = File('${dir.path}/settings.yaml');
      await temp.writeAsString(updated, flush: true);
      final result = await Process.run('chmod', ['600', temp.path]);
      if (result.exitCode != 0) {
        throw const FileSystemException('Cannot protect settings file');
      }
      await temp.rename(file.path);
    } finally {
      await dir.delete(recursive: true);
    }
  }
}
