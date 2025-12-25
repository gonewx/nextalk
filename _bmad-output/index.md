# Nextalk 项目文档索引

## 项目概览

| 属性 | 值 |
|------|-----|
| **项目类型** | Multi-part (Flutter 客户端 + Fcitx5 C++ 插件) |
| **主要语言** | Dart, C++ |
| **架构模式** | 双进程混合架构 (IPC via Unix Domain Socket) |
| **目标平台** | Linux (X11/Wayland) |

## 快速参考

### 技术栈

| 组件 | 技术 |
|------|------|
| 前端 UI | Flutter 3.x+ (Dart) |
| ASR 引擎 | Sherpa-onnx (C-API via FFI) |
| 音频采集 | PortAudio v19 |
| 后端插件 | C++17 (Fcitx5 Addon) |
| 进程通信 | Unix Domain Socket |

### 项目结构

```
nextalk/
├── voice_capsule/      # Flutter 客户端
├── addons/fcitx5/      # Fcitx5 C++ 插件
├── docs/               # 设计文档
├── scripts/            # DevOps 脚本
├── libs/               # 预编译库
├── packaging/          # 打包资源
└── Makefile            # 构建入口
```

---

## 生成的文档

### 核心文档

- [项目概览](./project-overview.md) - 项目简介、技术栈、架构概述
- [源码树分析](./source-tree-analysis.md) - 目录结构、关键文件、数据流向
- [集成架构](./integration-architecture.md) - 双进程通信、协议定义、交互流程
- [组件清单](./component-inventory.md) - UI 组件、服务层、FFI 绑定列表
- [开发指南](./development-guide.md) - 环境搭建、构建命令、调试技巧

### 状态文件

- [project-scan-report.json](./project-scan-report.json) - 扫描状态跟踪

---

## 现有设计文档

- [产品需求文档 (PRD)](../docs/prd.md) - 功能需求、非功能需求、Epic 列表
- [架构文档](../docs/architecture.md) - 详细技术架构、组件设计、协议定义
- [前端 UI/UX 规范](../docs/front-end-spec.md) - 视觉规范、动画参数、交互流程

---

## 快速开始

```bash
# 构建所有组件
make build

# 安装 Fcitx5 插件
make install-addon

# 开发模式运行
make run

# 运行测试
make test

# 查看所有命令
make help
```

---

## AI 辅助开发指南

### 理解项目

1. 阅读 [项目概览](./project-overview.md) 了解整体架构
2. 查看 [源码树分析](./source-tree-analysis.md) 定位关键文件
3. 参考 [集成架构](./integration-architecture.md) 理解双进程通信

### 修改代码

- **Flutter UI 相关**: 查看 [组件清单](./component-inventory.md) 的 UI 组件部分
- **服务逻辑**: 查看 [组件清单](./component-inventory.md) 的服务层部分
- **Fcitx5 插件**: 参考 [集成架构](./integration-architecture.md) 的协议定义

### 添加新功能

1. 参考 [架构文档](../docs/architecture.md) 确保符合设计
2. 查看 [开发指南](./development-guide.md) 了解开发流程
3. 遵循 [前端规范](../docs/front-end-spec.md) 保持 UI 一致性

---

## 相关链接

- **BMAD 工作流状态**: [bmm-workflow-status.yaml](./bmm-workflow-status.yaml)
- **Sprint 状态**: [implementation-artifacts/sprint-status.yaml](./implementation-artifacts/sprint-status.yaml)
- **项目 README**: [../README.md](../README.md)
- **CLAUDE.md 开发指南**: [../CLAUDE.md](../CLAUDE.md)

---

*文档生成日期: 2025-12-25*
*扫描模式: Deep Scan*
*工作流版本: 1.2.0*
