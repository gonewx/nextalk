# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 回复语言

请用简体中文回复

## 项目概述

**Nextalk** 是一款专为 Linux 设计的高性能离线语音输入应用，采用 Flutter 前端 + Fcitx5 C++ 插件的混合架构。

核心特性:
- 离线语音识别 (Sherpa-onnx 流式双语模型)
- 真透明无边框胶囊悬浮窗 UI
- 通过 Unix Domain Socket 与 Fcitx5 通信实现文本上屏
- 端到端延迟 < 20ms

## 架构

项目采用 Monorepo 结构，包含两个通过 IPC 通信的独立进程:

```
nextalk/
├── docs/               # PRD、架构文档、UX 规范
├── scripts/            # DevOps 脚本
├── libs/               # 预编译动态库 (.so)
│   ├── libsherpa-onnx-c-api.so
│   └── libonnxruntime.so
├── addons/             # [后端] Fcitx5 C++ 插件
│   └── fcitx5/
└── voice_capsule/      # [前端] Flutter 客户端
    ├── linux/          # CMakeLists.txt (链接配置)
    └── lib/
        ├── ffi/        # Dart FFI 绑定 (sherpa_ffi.dart, portaudio_ffi.dart)
        └── services/   # 业务逻辑 (sherpa_service.dart, fcitx_client.dart, model_manager.dart)
```

**IPC 协议**: Unix Domain Socket (`$XDG_RUNTIME_DIR/nextalk-fcitx5.sock`)
- 格式: `[4字节长度 LE] + [UTF-8 文本]`

**FFI 架构**: 零拷贝音频流水线
- PortAudio 采集 -> Dart `Pointer<Float>` -> Sherpa 推理 (同一内存指针)

## 技术栈

| 组件 | 技术 |
| :--- | :--- |
| 前端 UI | Flutter 3.x+ (Dart) |
| ASR 引擎 | Sherpa-onnx (C-API via dart:ffi) |
| 音频采集 | PortAudio v19 (C-API via dart:ffi) |
| 后端插件 | C++17 (Fcitx5 插件) |
| 进程通信 | Unix Domain Socket |

## 开发命令

### Flutter 客户端 (voice_capsule/)

```bash
# 构建 Linux 应用
cd voice_capsule && flutter build linux

# 开发模式运行
cd voice_capsule && flutter run -d linux

# 运行测试
cd voice_capsule && flutter test
```

### Fcitx5 插件 (addons/fcitx5/)

```bash
# 编译插件
cd addons/fcitx5 && mkdir -p build && cd build && cmake .. && make

# 安装插件 (需要配置脚本)
./scripts/install_addon.sh
```

## 模型管理

模型采用"首次运行下载"策略:
- 存储路径: `~/.local/share/nextalk/models`
- 模型: `sherpa-onnx-streaming-zipformer-bilingual-zh-en`

## BMAD 工作流

项目使用 BMAD Method 进行开发管理:
- 当前状态: Solutioning 阶段 (Phase 2)
- 下一步: 创建 Epics & Stories (`/bmad:bmm:workflows:create-epics-and-stories`)
- 状态跟踪: `_bmad-output/bmm-workflow-status.yaml`

## 禁止行为

- 不要自作主张添加空行或进行"代码格式化"
- 不要创建 "chore: 添加空行" 类型的提交
- 只修改任务明确要求的内容

## 用户手工维护区域

<!--
在此区域添加您的个人项目笔记、配置、工作流程等内容
此区域内容不会被文档更新脚本覆盖
-->

- 如果遇到网络问题，请尝试使用网络代理 http://127.0.0.1:2080 访问

- 遇到反复无法修复的问题或有不熟悉的第三方库, 尝试使用 `mcp__deepwiki` 工具的`ask_question`方法，查阅最新的文档，以找到最正确的修复方法 。

- 项目地址是: k2-fsa/sherpa-onnx
---
