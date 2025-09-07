# 更新日志

所有重要更改都将记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
并且本项目遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [未发布]

### 计划功能
- 多语言支持（英语、日语、韩语等）
- 云端同步配置
- 自定义语音模型支持
- 插件系统
- 移动端配套应用

## [0.1.0] - 2024-01-06

### 新增
- 🎙️ 实时语音识别核心功能
- ⌨️ 全局快捷键支持（可自定义）
- 🖱️ 自动文本注入到光标位置
- 📋 剪贴板回退机制
- 🔧 系统托盘集成
- 🔄 WebSocket 自动重连机制
- 📝 YAML 配置文件支持
- 🎯 多应用兼容性处理
- 📊 性能监控和日志系统
- 🏗️ 完整的测试套件
- 📦 跨平台打包支持（Windows/macOS/Linux）
- 🐳 Docker 容器化支持
- 🔨 自动化构建和发布流程

### 核心模块
- **音频模块** (`nextalk.audio`)
  - 音频采集管理器
  - 设备检测和切换
  - 实时音频流处理
  
- **网络模块** (`nextalk.network`)
  - WebSocket 客户端
  - FunASR 协议实现
  - 连接管理和错误恢复
  
- **输入模块** (`nextalk.input`)
  - 全局快捷键监听
  - 快捷键冲突检测
  - 键盘事件处理
  
- **输出模块** (`nextalk.output`)
  - 智能文本注入
  - 剪贴板操作
  - 应用兼容性处理
  
- **界面模块** (`nextalk.ui`)
  - 系统托盘图标
  - 上下文菜单
  - 状态指示器
  
- **核心模块** (`nextalk.core`)
  - 主控制器
  - 会话管理
  - 状态机实现

### 平台支持
- ✅ Windows 10/11 (64-bit)
- ✅ macOS 10.15+
- ✅ Linux (Ubuntu 20.04+, Fedora 34+)

### 依赖项
- Python 3.8+
- WebSockets 12.0+
- PyYAML 6.0+
- pynput 1.7.6+
- pyautogui 0.9.54+
- sounddevice 0.4.6+
- numpy 1.21.0+
- PyQt6 6.4.0+ (GUI 可选)

### 已知问题
- 部分输入法可能影响文本注入准确性
- macOS 首次运行需要授予辅助功能权限
- Linux Wayland 环境下快捷键可能受限
- 高 DPI 显示器下托盘图标可能模糊

### 贡献者
- NexTalk Team

---

## 版本规则

- **主版本号（MAJOR）**：不兼容的 API 更改
- **次版本号（MINOR）**：向后兼容的新功能
- **修订号（PATCH）**：向后兼容的错误修复

## 支持

- 问题反馈：[GitHub Issues](https://github.com/nextalk/nextalk/issues)
- 文档：[https://nextalk.dev/docs](https://nextalk.dev/docs)
- 邮箱：contact@nextalk.dev