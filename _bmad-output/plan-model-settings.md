# 模型配置功能实现计划

## 功能需求

1. **模型版本选择** - 通过托盘菜单切换 int8 / 标准版本
2. **模型下载地址配置** - 可自定义模型下载 URL

## 现状分析

### 当前问题
- `SherpaService._findModelFile()` 返回第一个匹配的 `.onnx` 文件，行为不确定
- 模型 URL 硬编码在 `ModelManager._downloadUrl`
- 无配置存储服务

### 现有资源
- `SharedPreferences` 已在 `pubspec.yaml` 中
- `WindowService` 已有使用 SharedPreferences 的模式参考
- 模型目录同时包含 int8 和标准版本文件

## 实现方案

### 1. 新建 `SettingsService` (配置服务)

```
lib/services/settings_service.dart
```

- 单例模式，与 `WindowService` 风格一致
- SharedPreferences 键名前缀 `nextalk_`
- 配置项：
  - `nextalk_model_type`: `int8` | `standard` (默认 `int8`)
  - `nextalk_custom_model_url`: 自定义下载 URL (空表示使用默认)

### 2. 修改 `SherpaService._findModelFile()`

```dart
// 当前实现 - 返回第一个匹配项
String? _findModelFile(String modelDir, String prefix) {
  // ... 返回第一个 prefix*.onnx
}

// 新实现 - 根据 useInt8 参数精确匹配
String? _findModelFile(String modelDir, String prefix, {bool useInt8 = true}) {
  // 优先查找指定版本
  // useInt8=true  -> prefix*.int8.onnx
  // useInt8=false -> prefix*.onnx (排除 .int8.onnx)
}
```

### 3. 修改 `SherpaConfig` 添加模型类型

```dart
class SherpaConfig {
  final String modelDir;
  final bool useInt8Model;  // 新增
  // ...
}
```

### 4. 修改 `ModelManager`

- 将 `_downloadUrl` 改为可配置
- 新增 `setCustomDownloadUrl(String? url)` 方法
- 新增 `getEffectiveDownloadUrl()` 方法

### 5. 修改 `TrayService` 添加设置子菜单

```
菜单结构：
├─ Nextalk (标题)
├─ ─────────
├─ 显示 / 隐藏
├─ 重新连接 Fcitx5
├─ 模型设置 ▶
│   ├─ ✓ int8 版本 (更快)
│   ├─   标准版本 (更准)
│   ├─ ─────────
│   └─   自定义下载地址...
├─ ─────────
└─ 退出
```

### 6. 模型切换流程

当用户切换模型版本时：
1. 保存配置到 SharedPreferences
2. 如果 Pipeline 正在运行，停止录音
3. 释放当前 SherpaService
4. 使用新配置重新初始化 SherpaService
5. 更新 Pipeline 引用

### 7. 自定义下载地址处理

- 托盘菜单点击"自定义下载地址..."
- 方案 A: 打开配置文件 (YAML/JSON) 让用户编辑
- 方案 B: 复制当前 URL 到剪贴板，提示用户修改配置文件

## 文件变更清单

| 文件 | 操作 | 说明 |
|-----|------|-----|
| `lib/services/settings_service.dart` | 新建 | 配置服务 |
| `lib/constants/settings_constants.dart` | 新建 | 配置键名常量 |
| `lib/services/sherpa_service.dart` | 修改 | `_findModelFile` 支持版本选择 |
| `lib/services/model_manager.dart` | 修改 | 支持自定义下载 URL |
| `lib/services/tray_service.dart` | 修改 | 添加设置子菜单 |
| `lib/constants/tray_constants.dart` | 修改 | 添加新菜单项常量 |
| `lib/main.dart` | 修改 | 初始化 SettingsService |
| `test/services/settings_service_test.dart` | 新建 | 单元测试 |

## 用户确认的决策

1. **切换模型后立即生效** - 需要实现热切换 Pipeline
2. **自定义 URL 通过配置文件** - 使用 `~/.config/nextalk/settings.yaml`

## 详细实现步骤

### Step 1: 创建 SettingsService

```dart
// lib/services/settings_service.dart
class SettingsService {
  static final instance = SettingsService._();

  // SharedPreferences 存储运行时配置
  // YAML 文件存储高级配置 (如自定义 URL)

  Future<void> initialize();

  // 模型类型
  ModelType get modelType;
  Future<void> setModelType(ModelType type);

  // 自定义 URL (从 YAML 读取)
  String? get customModelUrl;

  // 打开配置目录
  Future<void> openConfigDirectory();
}

enum ModelType { int8, standard }
```

### Step 2: 创建配置文件结构

```yaml
# ~/.config/nextalk/settings.yaml
model:
  # 自定义下载地址 (留空使用默认)
  custom_url: ""

  # 模型版本: int8 | standard
  type: int8
```

### Step 3: 修改 SherpaService

```dart
String? _findModelFile(String modelDir, String prefix, {bool useInt8 = true}) {
  final suffix = useInt8 ? '.int8.onnx' : '.onnx';
  // 精确匹配，不再依赖遍历顺序
}
```

### Step 4: 实现模型热切换

```dart
// 在 main.dart 或 HotkeyController 中
Future<void> switchModelType(ModelType newType) async {
  // 1. 停止当前录音
  await _pipeline?.stopCapture();

  // 2. 释放 SherpaService
  _sherpaService?.dispose();

  // 3. 创建新的 SherpaService
  _sherpaService = SherpaService();
  final config = SherpaConfig(
    modelDir: modelManager.modelPath,
    useInt8Model: newType == ModelType.int8,
  );
  await _sherpaService!.initialize(config);

  // 4. 更新 Pipeline 引用
  _pipeline?.updateSherpaService(_sherpaService!);

  // 5. 保存配置
  await SettingsService.instance.setModelType(newType);
}
```

### Step 5: 更新托盘菜单

```dart
// tray_service.dart
Future<void> _buildMenu() async {
  final currentType = SettingsService.instance.modelType;

  final menu = Menu();
  await menu.buildFrom([
    MenuItemLabel(label: TrayConstants.menuTitle, enabled: false),
    MenuSeparator(),
    MenuItemLabel(label: TrayConstants.menuShowHide, onClicked: (_) => _toggleWindow()),
    MenuItemLabel(label: TrayConstants.menuReconnectFcitx, onClicked: (_) => _reconnectFcitx()),
    SubMenu(
      label: TrayConstants.menuModelSettings,
      children: [
        MenuItemCheckbox(
          label: TrayConstants.menuModelInt8,
          checked: currentType == ModelType.int8,
          onClicked: (_) => _switchModel(ModelType.int8),
        ),
        MenuItemCheckbox(
          label: TrayConstants.menuModelStandard,
          checked: currentType == ModelType.standard,
          onClicked: (_) => _switchModel(ModelType.standard),
        ),
        MenuSeparator(),
        MenuItemLabel(
          label: TrayConstants.menuOpenConfig,
          onClicked: (_) => SettingsService.instance.openConfigDirectory(),
        ),
      ],
    ),
    MenuSeparator(),
    MenuItemLabel(label: TrayConstants.menuExit, onClicked: (_) => _exitApp()),
  ]);
  await _systemTray.setContextMenu(menu);
}
```

## 文件变更清单 (最终版)

| 文件 | 操作 | 说明 |
|-----|------|-----|
| `lib/services/settings_service.dart` | 新建 | 配置服务 (SharedPreferences + YAML) |
| `lib/constants/settings_constants.dart` | 新建 | 配置键名和路径常量 |
| `lib/services/sherpa_service.dart` | 修改 | `_findModelFile` 支持精确版本选择 |
| `lib/services/model_manager.dart` | 修改 | 从 SettingsService 读取自定义 URL |
| `lib/services/tray_service.dart` | 修改 | 添加模型设置子菜单 |
| `lib/constants/tray_constants.dart` | 修改 | 添加新菜单项常量 |
| `lib/services/audio_inference_pipeline.dart` | 修改 | 添加 `updateSherpaService` 方法 |
| `lib/main.dart` | 修改 | 初始化 SettingsService，注册模型切换回调 |
| `test/services/settings_service_test.dart` | 新建 | 单元测试 |
