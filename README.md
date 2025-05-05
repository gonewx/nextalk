# NexTalk

轻量级实时本地语音识别与输入系统。

## 功能特性

- **本地语音识别**：使用Whisper和FunASR模型实现高质量的本地语音识别
- **实时转录**：低延迟的语音-文本转换
- **自动文本注入**：将识别的文本自动注入到当前活动窗口
- **热键激活**：通过可自定义热键快速启动/停止语音识别
- **多模型支持**：支持Whisper和FunASR模型，优化不同语言的识别效果
- **系统托盘集成**：直观的状态指示和快速访问设置
- **高效资源利用**：智能语音活动检测(VAD)降低资源消耗
- **跨平台支持**：兼容主流操作系统(计划中)

## 快速入门

请查看[安装指南](docs/setup_guide.md)获取完整的安装和配置说明，包括：

- 系统要求
- 依赖安装
- 环境配置
- 首次运行指南

## 使用方法

基本使用步骤：

1. 使用统一启动脚本：`python scripts/nextalk.py start`
2. 或单独启动组件：
   - 服务器：`python scripts/nextalk.py server`
   - 客户端：`python scripts/nextalk.py client`
3. 使用默认热键(Ctrl+Shift+Space)激活语音识别
4. 开始讲话，识别的文本将自动输入到当前活动窗口

调试模式启动：`python scripts/nextalk.py start --debug`

查看帮助信息：`python scripts/nextalk.py --help`

更多详细信息请查看[用户指南](docs/user_guide.md)获取使用说明、配置选项和故障排除方法。

## 贡献

欢迎贡献代码、报告问题或提出改进建议！请查看[开发者指南](docs/developer_guide.md)了解开发环境设置、代码组织和贡献流程。

项目架构详情请参阅[架构文档](docs/architecture.md)。

## 许可证

本项目采用MIT许可证 - 详情请查看[LICENSE](LICENSE)文件。 