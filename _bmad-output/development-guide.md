# Nextalk 开发指南

## 系统要求

### 运行环境

- Linux (Ubuntu 22.04+ 推荐)
- Fcitx5 输入法框架
- ALSA 或 PulseAudio 音频系统
- X11 或 Wayland 显示服务器

### 开发环境

| 工具 | 版本 | 安装命令 |
|------|------|----------|
| Flutter | 3.x+ | [官方安装指南](https://flutter.dev/docs/get-started/install/linux) |
| CMake | 3.16+ | `sudo apt install cmake` |
| GCC/G++ | C++17 支持 | `sudo apt install build-essential` |
| Fcitx5 开发库 | 5.0+ | `sudo apt install fcitx5-dev` |
| PortAudio | v19 | `sudo apt install libportaudio2 portaudio19-dev` |

## 快速开始

### 1. 克隆仓库

```bash
git clone <repo-url>
cd nextalk_fcitx5_v2
```

### 2. 安装依赖

```bash
# 系统依赖
sudo apt install fcitx5 fcitx5-dev libportaudio2 portaudio19-dev

# Flutter 依赖
cd voice_capsule && flutter pub get
```

### 3. 构建项目

```bash
# 使用 Makefile (推荐)
make build

# 或分别构建
make build-flutter    # Flutter 客户端
make build-addon      # Fcitx5 插件
```

### 4. 安装插件

```bash
make install-addon
# 或
./scripts/install_addon.sh
```

### 5. 运行

```bash
make run
# 或
cd voice_capsule && flutter run -d linux
```

## 开发工作流

### 日常开发

```bash
# 开发模式运行 (热重载)
make dev

# 运行测试
make test

# 代码分析
make analyze
```

### 构建发布版本

```bash
# Release 构建
make build-flutter

# 构建安装包
make package
# 或指定格式
./scripts/build-pkg.sh --deb
./scripts/build-pkg.sh --rpm
```

### 清理

```bash
make clean           # 清理所有
make clean-flutter   # 仅清理 Flutter
make clean-addon     # 仅清理插件
```

## 项目配置

### 模型配置

模型采用首次运行下载策略，存储在:

```
~/.local/share/nextalk/models/
```

支持的模型版本:

| 版本 | 说明 |
|------|------|
| `int8` | 量化版本，速度快，内存占用小 |
| `standard` | 标准版本，精度高 |

配置文件位置:

```yaml
# ~/.config/nextalk/settings.yaml
model:
  custom_url: ""    # 自定义下载地址
  type: int8        # 模型版本
```

### 快捷键配置

默认快捷键: `Right Alt`

支持通过 Fcitx5 插件配置，格式:

```
config:hotkey:<key_spec>
```

示例:
- `config:hotkey:Alt_R` (默认)
- `config:hotkey:Control+Shift+Space`
- `config:hotkey:F12`

## 调试技巧

### Flutter 客户端调试

```bash
# 启用详细日志
cd voice_capsule && flutter run -d linux --verbose

# 查看诊断日志
tail -f ~/.local/share/nextalk/logs/*.log
```

### Fcitx5 插件调试

```bash
# 重启 Fcitx5 并查看日志
fcitx5 -r -d

# 查看插件日志
journalctl --user -u fcitx5 -f
# 或
tail -f ~/.local/share/fcitx5/logs/*.log
```

### Socket 通信调试

```bash
# 检查 Socket 文件
ls -la $XDG_RUNTIME_DIR/nextalk*.sock

# 监听 Socket 通信 (需要 socat)
socat -v UNIX-LISTEN:/tmp/test.sock,fork -
```

## 测试

### 运行所有测试

```bash
make test
```

### Flutter 单元测试

```bash
cd voice_capsule
flutter test

# 运行特定测试
flutter test test/specific_test.dart

# 生成覆盖率报告
flutter test --coverage
```

## 代码规范

### Dart 代码

- 遵循 `flutter_lints` 规则 (见 `analysis_options.yaml`)
- 使用 `flutter analyze` 检查问题

### C++ 代码

- 遵循 C++17 标准
- 使用 Fcitx5 日志宏: `NEXTALK_INFO()`, `NEXTALK_DEBUG()`, `NEXTALK_ERROR()`

## 架构决策

### 为什么使用 Flutter?

- Linux 上最佳的真透明、无边框渲染能力
- 丰富的动画 API，实现呼吸灯等效果
- dart:ffi 提供零开销 C 互操作

### 为什么使用 Fcitx5 插件?

- 原生 Wayland 支持 (快捷键监听)
- 标准输入法协议，跨应用文本注入
- 焦点锁定机制，解决窗口切换问题

### 为什么使用 Unix Domain Socket?

- 低延迟本地通信
- 简单可靠，无需额外依赖
- 权限控制 (chmod 600)

## 常见问题

### 1. 模型下载失败

检查网络连接，或配置代理:

```yaml
# ~/.config/nextalk/settings.yaml
model:
  custom_url: "https://your-mirror/model.tar.bz2"
```

### 2. 插件未加载

```bash
# 检查插件文件
ls ~/.local/lib/fcitx5/nextalk.so
ls ~/.local/share/fcitx5/addon/nextalk.conf

# 重启 Fcitx5
fcitx5 -r
```

### 3. 音频设备问题

```bash
# 检查 PortAudio 设备
pactl list sources

# 确保麦克风权限
sudo usermod -aG audio $USER
```

### 4. Wayland 下快捷键不响应

确保 Fcitx5 插件正确安装，快捷键由插件侧监听。

## 发布流程

### 1. 更新版本号

- `voice_capsule/pubspec.yaml`: `version: x.y.z`
- `addons/fcitx5/CMakeLists.txt`: `VERSION x.y.z`

### 2. 构建测试

```bash
make clean
make build
make test
```

### 3. 构建安装包

```bash
./scripts/build-pkg.sh --all
ls dist/
```

### 4. 测试安装包

```bash
# Ubuntu
sudo dpkg -i dist/nextalk_x.y.z-1_amd64.deb

# Fedora
sudo rpm -i dist/nextalk-x.y.z-1.x86_64.rpm
```
