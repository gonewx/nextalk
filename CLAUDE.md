# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

NexTalk 是一个个人轻量级实时语音识别与输入系统，基于 FunASR 技术，提供中文语音识别和智能文本注入功能。

## 回复语言

使用简体中文回复

## 遇到问题时

use mcp__deepwiki 查看相关项目文档。不要简单的使用 read_wiki_contents, 要提出具体问题。


## 核心架构

### 模块结构
```
nextalk/
├── audio/          # 音频采集 (capture.py, device.py)
├── config/         # 配置管理 (manager.py, models.py)
├── core/           # 核心控制 (controller.py, session.py)
├── input/          # 输入控制 (hotkey.py, listener.py)
├── network/        # 网络通信 (ws_client.py, protocol.py)
├── output/         # 文本输出 (text_injector.py)
├── ui/             # 用户界面 (tray.py, menu.py, icons.py)
└── utils/          # 工具函数 (logger.py, monitor.py, system.py)
```

### 配置系统

主配置文件: `config/nextalk.yaml`
- 服务器配置: host/port/SSL 设置
- 音频参数: 采样率、声道、设备选择
- 快捷键: 默认 `ctrl+shift+space`
- UI 设置: 系统托盘、通知、语言
- 识别模式: 2pass 模式，支持 ITN 和标点


**依赖关系**:
- NexTalk 依赖 FunASR WebSocket 服务 (localhost:10095)
- 首次运行会下载约 2-3GB 语音识别模型

### 测试架构

- **单元测试**: `tests/*/test_*.py` - 每个模块对应的测试
- **集成测试**: `tests/integration/` - 完整工作流测试
- **端到端测试**: `tests/e2e/` - 用户场景测试
- **测试配置**: pytest + asyncio + coverage

### 开发注意事项

1. **异步编程**: 核心使用 asyncio，注意 async/await 使用
2. **类型检查**: 启用了 mypy 严格模式，需要完整类型标注
3. **跨平台**: 支持 Windows/macOS/Linux，注意平台特定代码
4. **权限要求**:
   - macOS 需要辅助功能权限
   - Linux 需要 X11/Wayland 支持
   - Windows 建议管理员权限
5. **依赖安装常见问题**:
   - PyGObject 安装失败: 需要 `libgirepository-2.0-dev` 等系统依赖
   - 参考 `docs/INSTALL.md` 中的故障排除部分

### 常见开发任务

- 修改快捷键: 更新 `config/nextalk.yaml` hotkey 部分
- 添加新的识别语言: 修改 `recognition.language_model`
- 调整音频参数: 更新 `audio` 配置段
- 自定义文本注入: 修改 `output/text_injector.py`
- 添加新的 UI 功能: 扩展 `ui/` 模块

