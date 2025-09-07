# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

NexTalk 是一个个人轻量级实时语音识别与输入系统，基于 FunASR 技术，提供中文语音识别和智能文本注入功能。

## 回复语言

使用简体中文回复

## 遇到问题时

use mcp__deepwiki 查看相关项目文档。不要简单的使用 read_wiki_contents, 要提出具体问题。

## 常用开发命令

### 测试命令
```bash
# 运行完整测试套件
make test

# 运行快速单元测试 
make test-quick

# 运行集成测试
make test-integration

# 使用 pytest 直接运行
python -m pytest tests/ -v
```

### 代码质量检查
```bash
# 运行所有代码检查
make lint

# 单独运行各项检查
python -m flake8 nextalk/     # 代码风格检查
python -m mypy nextalk/       # 类型检查
python -m black nextalk/      # 代码格式检查
python -m black --check nextalk/  # 仅检查不修改

# 自动格式化代码
make format
```

### 构建和打包
```bash
# 构建可执行文件
make build

# 构建带 GUI 版本
make build-gui

# 创建分发包
make package

# 完整发布流程
make release
```

### 开发运行
```bash
# 启动完整系统 (FunASR 服务器 + NexTalk)
python start_all.py

# 仅启动 NexTalk (需要先启动 FunASR 服务器)
python -m nextalk
# 或
nextalk

# 调试模式运行
make debug
```

### 依赖管理
```bash
# 安装运行时依赖
make install

# 安装开发依赖
make dev

# 检查依赖状态
make check-deps
```

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

### 关键组件

1. **Controller** (`core/controller.py:31-40`)
   - 主状态机: UNINITIALIZED → INITIALIZING → READY → ACTIVE
   - 协调所有模块，管理应用生命周期
   - 异步架构，基于 asyncio

2. **FunASR 集成**
   - `funasr_wss_server.py` - FunASR WebSocket 服务器 
   - `network/ws_client.py` - WebSocket 客户端连接
   - 支持自动重连和错误恢复

3. **音频处理**
   - 实时音频采集，支持设备选择
   - 配置参数: 采样率 16000Hz，单声道
   - 分块处理: [5, 10, 5] chunk_size

4. **文本注入系统**
   - 自动将识别结果注入到光标位置
   - 支持剪贴板回退机制
   - Linux 下强制使用剪贴板模式避免权限问题

### 配置系统

主配置文件: `config/nextalk.yaml`
- 服务器配置: host/port/SSL 设置
- 音频参数: 采样率、声道、设备选择
- 快捷键: 默认 `ctrl+shift+space`
- UI 设置: 系统托盘、通知、语言
- 识别模式: 2pass 模式，支持 ITN 和标点

### 启动流程

**必需步骤**:
1. 启动 FunASR 服务器: `python funasr_wss_server.py`
2. 等待模型加载完成 (显示 "model loaded!")
3. 启动 NexTalk: `python -m nextalk`

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

### 常见开发任务

- 修改快捷键: 更新 `config/nextalk.yaml` hotkey 部分
- 添加新的识别语言: 修改 `recognition.language_model`
- 调整音频参数: 更新 `audio` 配置段
- 自定义文本注入: 修改 `output/text_injector.py`
- 添加新的 UI 功能: 扩展 `ui/` 模块

### 调试技巧

1. 启用调试日志: 设置 `logging.level: "DEBUG"`
2. 使用测试脚本: `test_im_injection.py`, `demo_im_injection.py`
3. 检查网络连接: 确认 FunASR 服务器状态
4. 音频设备测试: 使用 `scripts/verify_installation.py`