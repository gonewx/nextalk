# Nextalk 项目概览

## 项目信息

| 属性 | 值 |
|------|-----|
| **项目名称** | Nextalk |
| **版本** | 0.1.0 |
| **仓库类型** | Multi-part (多部件 Monorepo) |
| **主要语言** | Dart, C++ |
| **目标平台** | Linux (X11/Wayland) |

## 项目简介

**Nextalk** 是一款专为 Linux 设计的高性能离线语音输入应用。采用 Flutter 前端 + Fcitx5 C++ 插件的混合架构，通过 Unix Domain Socket 实现进程间通信。

### 核心特性

- **离线语音识别**: 基于 Sherpa-onnx 流式双语模型 (中英文)
- **低延迟**: 端到端延迟 < 20ms
- **真透明悬浮窗**: 无边框胶囊 UI，不干扰工作流程
- **Fcitx5 集成**: 通过输入法框架实现跨应用文本输入
- **Wayland 原生支持**: 快捷键监听和文本提交均支持 Wayland

## 技术栈

| 组件 | 技术 | 版本 | 用途 |
|------|------|------|------|
| **前端 UI** | Flutter (Dart) | 3.x+ | 透明悬浮窗、动画、用户交互 |
| **ASR 引擎** | Sherpa-onnx | 最新版 | 离线流式语音识别 |
| **音频采集** | PortAudio | v19 | Linux 跨平台音频 I/O |
| **语言绑定** | dart:ffi | Native | 零拷贝 FFI 互操作 |
| **进程通信** | Unix Domain Socket | 标准 | Flutter ↔ Fcitx5 通信 |
| **后端插件** | C++ | C++17 | Fcitx5 原生插件 |

## 项目结构

```
nextalk/
├── voice_capsule/        # [Part 1] Flutter 客户端
│   ├── lib/              # Dart 源码
│   │   ├── ffi/          # FFI 绑定 (Sherpa, PortAudio)
│   │   ├── services/     # 业务逻辑
│   │   ├── ui/           # Widget 组件
│   │   └── constants/    # 常量定义
│   ├── linux/            # Linux 构建配置
│   └── assets/           # 图标资源
│
├── addons/fcitx5/        # [Part 2] Fcitx5 C++ 插件
│   ├── src/              # C++ 源码
│   └── CMakeLists.txt    # CMake 构建
│
├── docs/                 # 设计文档
├── scripts/              # DevOps 脚本
├── libs/                 # 预编译动态库
├── packaging/            # DEB/RPM 打包资源
└── Makefile              # 项目级构建入口
```

## 架构模式

采用 **双进程混合架构**:

1. **Voice Capsule (进程 A)**: Flutter 桌面应用，负责 UI、音频采集、AI 推理
2. **Nextalk Addon (进程 B)**: Fcitx5 插件，负责快捷键监听、文本注入

两个进程通过三个 Unix Domain Socket 通信:

| Socket | 方向 | 用途 |
|--------|------|------|
| `nextalk-fcitx5.sock` | Flutter → 插件 | 文本提交 |
| `nextalk-fcitx5-cfg.sock` | Flutter → 插件 | 配置命令 |
| `nextalk-cmd.sock` | 插件 → Flutter | 控制命令 (toggle) |

## 现有文档

| 文档 | 路径 | 说明 |
|------|------|------|
| PRD | [docs/prd.md](../docs/prd.md) | 产品需求文档 |
| 架构文档 | [docs/architecture.md](../docs/architecture.md) | 技术架构设计 |
| 前端规范 | [docs/front-end-spec.md](../docs/front-end-spec.md) | UI/UX 设计规范 |
| README | [README.md](../README.md) | 项目入门指南 |
| 客户端 README | [voice_capsule/README.md](../voice_capsule/README.md) | Flutter 客户端说明 |

## 快速开始

```bash
# 构建所有组件
make build

# 运行开发模式
make run

# 安装 Fcitx5 插件
make install-addon

# 运行测试
make test
```

## 相关链接

- [开发指南](./development-guide.md)
- [源码树分析](./source-tree-analysis.md)
- [组件清单](./component-inventory.md)
