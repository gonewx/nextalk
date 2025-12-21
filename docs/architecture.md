# 架构文档: Nextalk

| 日期       | 版本 | 说明 | 作者 |
| :---       | :--- | :--- | :--- |
| 2025-12-21 | 1.1  | 完整架构设计 (Flutter/C++混合架构，模型动态下载) | 架构师 (Winston) |

## 1. 简介 (Introduction)

**Nextalk** 是一款专为 Linux 设计的高性能语音输入应用，采用混合架构 (Hybrid Architecture)。它结合了现代化的 **Flutter** 前端（负责 UI、流程编排和 AI 推理）与原生的 **C++** 引擎（Fcitx5 插件）来提供系统级输入能力。

系统设计为 **Monorepo (单体仓库)**，包含两个通过 IPC 通信的独立进程：
1.  **Voice Capsule (客户端)**: 一个独立的 Flutter 桌面应用，负责 UI 显示、音频采集、模型管理和语音识别。
2.  **Nextalk Addon (服务端)**: 一个轻量级的 Fcitx5 插件，负责接收指令并将文本注入到目标应用程序。

## 2. 高层架构 (High Level Architecture)

### 2.1 系统上下文图

```mermaid
graph TD
    User[用户语音] --> Mic[麦克风]
    Mic --> Audio[PortAudio (C语言库)]
    
    subgraph "进程 A: Voice Capsule (Flutter)"
        Audio -- "FFI (零拷贝)" --> Logic[Dart 业务逻辑]
        Logic -- "FFI (零拷贝)" --> Sherpa[Sherpa-onnx (AI 引擎)]
        Sherpa -- "文本流" --> Logic
        Logic -- "状态更新" --> UI[透明胶囊窗口]
        Logic -- "Socket 写入" --> IPC_Client[Dart Socket 客户端]
        ModelMgr[模型管理器] -- "下载/校验" --> Storage[本地存储 (~/.local)]
    end

    subgraph "进程 B: Fcitx5 守护进程"
        IPC_Client -- "Unix Domain Socket" --> IPC_Server[Nextalk 插件]
        IPC_Server -- "commitString" --> TargetApp[当前活动窗口]
    end
```

### 2.2 目录结构 (Monorepo)

项目采用严格的 Monorepo 结构，分离前后端代码与外部依赖。

```text
nextalk/
├── docs/                     # 设计文档 (PRD, 架构文档)
├── scripts/                  # DevOps 脚本 (安装插件, 编译辅助)
├── libs/                     # 外部预编译动态库 (.so)
│   ├── libsherpa-onnx-c-api.so
│   └── libonnxruntime.so
├── addons/                   # [后端] Fcitx5 C++ 插件
│   └── fcitx5/
│       ├── CMakeLists.txt
│       └── src/              # 原生 C++ 实现 (nextalk.cpp)
└── voice_capsule/            # [前端] Flutter 客户端
    ├── pubspec.yaml
    ├── linux/                # Linux 构建配置 (需修改 CMakeLists.txt)
    ├── assets/               # 仅包含图标、字体等轻量资源 (不含模型)
    └── lib/
        ├── main.dart         # UI 入口
        ├── ffi/              # 原生绑定层 ("大脑"的神经连接)
        │   ├── sherpa_ffi.dart
        │   └── portaudio_ffi.dart
        ├── services/         # 业务逻辑
        │   ├── sherpa_service.dart
        │   ├── model_manager.dart # 模型下载与管理
        │   └── fcitx_client.dart
        └── ui/               # Widget 组件定义
```

## 3. 技术栈 (Technology Stack)

| 组件 | 技术 | 版本 | 选型理由 |
| :--- | :--- | :--- | :--- |
| **前端 UI** | Flutter (Dart) | 3.x+ | 提供 Linux 上最佳的真透明、无边框渲染能力。 |
| **ASR 引擎** | Sherpa-onnx | 最新版 | 高性能、离线、支持流式识别，提供标准 C-API。 |
| **音频采集** | PortAudio | v19 | Linux 跨平台音频 I/O 的行业标准 (兼容 ALSA/Pulse)。 |
| **语言绑定** | `dart:ffi` | Native | 与 C 库进行零开销互操作。 |
| **进程通信** | Unix Domain Socket | 标准 | 简单、安全、低延迟的本地通信方案。 |
| **后端插件** | C++ | C++17 | 开发 Fcitx5 原生插件的硬性要求。 |

## 4. 核心组件设计 (Core Component Design)

### 4.1 Fcitx5 插件与协议

**角色**: 被动执行者。它监听文本指令并将其实际输入到上下文中。

*   **传输层**: Unix Domain Socket (Stream 模式)。
*   **路径策略**: 优先 `$XDG_RUNTIME_DIR/nextalk-fcitx5.sock` (回退方案: `/tmp/...`)。
*   **安全性**: Socket 文件权限必须设为 `0600` (仅所有者读写)。
*   **协议定义**:

| 偏移量 | 类型 | 大小 | 描述 |
| :--- | :--- | :--- | :--- |
| 0 | `uint32` | 4 | **长度 (Length)** (小端序 Little Endian)。后续文本字符串的字节长度。 |
| 4 | `bytes` | N | **载荷 (Payload)**。UTF-8 编码的待提交文本。 |

### 4.2 音频与 AI 流水线 (零拷贝 FFI)

为了满足 **NFR1 (延迟 < 200ms)**，音频流水线必须最大限度减少内存拷贝。

1.  **内存分配**: Dart 使用 `calloc` 分配一块堆外内存缓冲区 (`Pointer<Float>`)。
2.  **采集**: Dart 将此指针传递给 PortAudio 的 `Pa_ReadStream`。C 代码直接将 PCM 数据写入该内存地址。
3.  **推理**: Dart 将**同一个指针**传递给 Sherpa 的 `AcceptWaveform`。在流处理期间，Dart/C 边界之间没有数据拷贝发生。
4.  **结果**: 只有当 Sherpa 返回识别出的文本结果时，才将文本字符串复制到 Dart 托管内存中供 UI 显示。

**并发模型**:
*   **Main Isolate (主线程)**: 音频读取和推理调用虽然是阻塞的，但速度极快 (处理 100ms 音频块通常 <10ms)。为了简化架构，MVP 阶段运行在主 Isolate 中。
*   **Fallback (兜底)**: 如果在低端硬件上出现 UI 掉帧，则将该流水线移至 `Isolate.spawn` 后台运行。

### 4.3 FFI 接口定义

Dart FFI 绑定必须镜像 Sherpa-onnx 的 C-API。

```dart
// 绑定结构概念示例
typedef AcceptWaveformC = Void Function(Pointer<Void> stream, Int32 sampleRate, Pointer<Float> buffer, Int32 n);
typedef AcceptWaveformDart = void Function(Pointer<Void> stream, int sampleRate, Pointer<Float> buffer, int n);

class SherpaService {
  late DynamicLibrary _lib;
  late AcceptWaveformDart _acceptWaveform;
  
  void feedAudio(Pointer<Float> data, int samples) {
    _acceptWaveform(_stream, 16000, data, samples);
  }
}
```

### 4.4 模型管理 (Model Management)

为了减小安装包体积，模型文件采用 **"首次运行下载" (Download-on-Demand)** 策略。

1.  **存储路径**: 遵循 XDG Base Directory 规范。
    *   路径: `$XDG_DATA_HOME/nextalk/models` (默认 `~/.local/share/nextalk/models`)
2.  **启动流程**:
    *   App 启动 -> 检查模型文件完整性。
    *   **缺失**: 跳转至 `DownloadPage`，下载并解压模型包。
    *   **存在**: 初始化 Sherpa 引擎 -> 进入主界面。
3.  **模型源**: 托管于 HuggingFace 或 GitHub Releases 的 `zipformer` 压缩包。

## 5. 基础设施与构建系统

### 5.1 库链接策略

Flutter 的 Linux 构建使用 CMake。我们需要确保外部 `.so` 库被正确打包。

**链接配置 (`linux/CMakeLists.txt`)**:
1.  **系统库**: `libportaudio.so` 从系统动态链接 (假设用户已通过 `apt` 安装)。
2.  **打包库**: `libsherpa-onnx-c-api.so` 从项目的 `libs/` 目录复制到构建产物中。

### 5.2 RPATH 配置

确保二进制文件在运行时能找到打包的库：

```cmake
# 在 linux/CMakeLists.txt 中
install(FILES "${PROJECT_SOURCE_DIR}/../libs/libsherpa-onnx-c-api.so"
        DESTINATION "${CMAKE_INSTALL_PREFIX}/lib"
        COMPONENT Runtime)

# 设置 RPATH，让程序去可执行文件旁的 'lib' 目录查找依赖
set(CMAKE_INSTALL_RPATH "$ORIGIN/lib")
```

### 5.3 发布包布局

最终的构建产物 (Bundle) 结构如下，体积保持轻量化：

```text
bundle/
├── nextalk              # 可执行文件
├── lib/
│   ├── libsherpa-onnx-c-api.so  # 私有依赖库
│   └── libflutter_linux_gtk.so
└── data/                # Flutter 自身资源 (不含模型)
```

## 6. 安全与错误处理

*   **Socket 权限**: C++ 插件必须强制对 Socket 文件执行 `chmod 600`，防止其他用户的进程注入恶意指令。
*   **网络权限**: Flutter 客户端需要联网权限以执行模型下载。
*   **音频故障**: 如果 PortAudio 无法打开流 (例如设备被独占)，UI 必须显示视觉错误指示 (例如红灯变黄/灰)。
*   **下载校验**: 下载后必须校验 SHA256，防止文件损坏导致引擎崩溃。
