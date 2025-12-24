# Nextalk

专为 Linux 设计的高性能离线语音输入应用。

## 特性

- **离线识别**: 基于 Sherpa-onnx 的流式双语语音识别，无需联网
- **低延迟**: 端到端延迟 < 200ms，实时转录体验
- **透明悬浮窗**: 真透明无边框胶囊 UI，不干扰工作流程
- **Fcitx5 集成**: 通过输入法框架实现跨应用文本输入
- **模型配置**: 支持 int8/standard 模型切换，可自定义下载地址

## 系统要求

- Linux (支持 ALSA/PulseAudio)
- Fcitx5 输入法框架
- Flutter 3.x+ (仅开发时需要)

## 安装

### 从安装包安装 (推荐)

**Ubuntu/Debian:**
```bash
sudo dpkg -i nextalk_0.1.0-1_amd64.deb
```

**Fedora/CentOS/RHEL:**
```bash
sudo rpm -i nextalk-0.1.0-1.x86_64.rpm
```

安装完成后，Fcitx5 会自动重启以加载插件。

### 卸载

**Ubuntu/Debian:**
```bash
sudo dpkg -r nextalk
```

**Fedora/CentOS/RHEL:**
```bash
sudo rpm -e nextalk
```

> 用户数据保留在 `~/.local/share/nextalk/`，如需完全清理请手动删除。

## 从源码构建

### 1. 构建 Flutter 客户端

```bash
cd voice_capsule
flutter build linux
```

### 2. 安装 Fcitx5 插件

```bash
cd addons/fcitx5
mkdir -p build && cd build
cmake .. && make
./scripts/install_addon.sh
```

### 3. 运行

```bash
cd voice_capsule
flutter run -d linux
```

首次运行时，应用会自动下载语音识别模型 (~200MB)。

### 4. 构建安装包

```bash
# 构建 DEB 包 (Ubuntu/Debian)
./scripts/build-pkg.sh --deb

# 构建 RPM 包 (Fedora/CentOS)
./scripts/build-pkg.sh --rpm

# 构建全部格式
./scripts/build-pkg.sh --all
```

输出文件位于 `dist/` 目录。

## 配置

### 模型设置

通过系统托盘菜单可以:
- 切换模型版本 (int8 量化版 / standard 标准版)
- 打开配置目录

### 配置文件

高级配置位于 `~/.config/nextalk/settings.yaml`:

```yaml
model:
  # 自定义模型下载地址 (留空使用默认地址)
  custom_url: ""

  # 模型版本: int8 | standard
  type: int8
```

| 模型版本 | 说明 |
| :--- | :--- |
| `int8` | 量化版本，速度快，内存占用小 |
| `standard` | 标准版本，识别精度更高 |

## 架构

```
nextalk/
├── voice_capsule/    # Flutter 客户端 (UI + 语音识别)
├── addons/fcitx5/    # Fcitx5 C++ 插件 (文本上屏)
├── packaging/        # 打包资源 (DEB/RPM 模板)
├── libs/             # 预编译动态库
├── scripts/          # 构建和安装脚本
└── docs/             # 设计文档
```

详细架构设计请参阅 [docs/architecture.md](docs/architecture.md)。

## 开发

### 运行测试

```bash
cd voice_capsule
flutter test
```

### 项目结构

```
voice_capsule/lib/
├── ffi/              # FFI 绑定 (PortAudio, Sherpa-onnx)
├── constants/        # 常量定义
├── services/         # 业务逻辑
│   ├── audio_capture.dart
│   ├── sherpa_service.dart
│   ├── model_manager.dart
│   ├── settings_service.dart
│   ├── tray_service.dart
│   └── fcitx_client.dart
└── ui/               # Widget 组件
```

## 许可证

MIT License
