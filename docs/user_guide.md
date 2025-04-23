# NexTalk 用户指南

NexTalk是一个轻量级的实时本地语音识别和输入系统，能够将您的语音转换为文本并注入到任何活动应用程序中。本指南将介绍如何使用NexTalk的各项功能。

## 目录

- [启动NexTalk](#启动nextalk)
- [基本操作](#基本操作)
- [系统托盘图标](#系统托盘图标)
- [模型选择](#模型选择)
- [常见问题排除](#常见问题排除)

## 启动NexTalk

NexTalk由服务器和客户端两部分组成，需要分别启动。

### 启动服务器

服务器负责处理语音识别，您需要首先启动服务器：

```bash
# 在项目根目录下运行
./scripts/run_server.py
```

或者：

```bash
python -m nextalk_server.main
```

服务器启动后，您将看到类似以下的输出：

```
正在启动NexTalk服务器，端口:8000...
服务器配置: 模型=small.en-int8, 设备=cuda
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

### 启动客户端

在服务器启动后，您可以在另一个终端中启动客户端：

```bash
# 在项目根目录下运行
./scripts/run_client.py
```

或者：

```bash
python -m nextalk_client.main
```

客户端启动后，将在系统托盘区域显示一个图标，表示应用已准备就绪。

## 基本操作

### 激活/停用语音识别

NexTalk使用热键来控制语音识别的开启和关闭：

1. **激活语音识别**：按下热键组合（默认为 `Ctrl+Shift+Space`）并保持按住
2. **开始说话**：当系统托盘图标变为"监听"状态时，开始对着麦克风说话
3. **停止识别**：松开热键组合
4. **查看结果**：识别结果将自动输入到当前活动的应用程序中

> **注意**：首次使用时可能需要下载语音识别模型，这可能需要一些时间，请耐心等待。

### 修改热键

默认热键为 `Ctrl+Shift+Space`，您可以通过编辑配置文件来修改：

1. 打开 `~/.config/nextalk/config.ini`
2. 在 `[Client]` 部分修改 `hotkey` 选项
3. 保存文件并重启客户端

示例配置：

```ini
[Client]
hotkey=alt+shift+v
server_url=ws://127.0.0.1:8000/ws/stream
language=zh
```

## 系统托盘图标

系统托盘图标反映了NexTalk的当前状态：

| 图标状态 | 描述 |
|---------|------|
| 闲置 | 应用已启动但未激活语音识别 |
| 监听中 | 正在捕获音频并发送到服务器 |
| 处理中 | 正在处理语音识别 |
| 错误 | 出现问题，查看错误通知或日志 |

右键点击系统托盘图标可以访问上下文菜单：

- **选择模型**：切换不同大小的语音识别模型
- **退出**：关闭NexTalk应用

## 模型选择

NexTalk提供了三种不同大小的语音识别模型，可以根据您的硬件性能和识别精度需求进行选择：

| 模型 | 性能 | 精度 | 资源需求 |
|-----|------|------|---------|
| tiny.en | 最快 | 较低 | 最低（约500MB内存） |
| small.en | 中等 | 中等 | 中等（约1GB内存） |
| base.en | 较慢 | 最高 | 较高（约2GB内存） |

要切换模型：

1. 右键点击系统托盘图标
2. 选择 "选择模型" 子菜单
3. 点击所需的模型大小

> **注意**：首次切换到新模型时，可能需要下载相应的模型文件，这可能需要一些时间。

## 常见问题排除

### 连接问题

如果客户端无法连接到服务器：

1. 确保服务器已经启动并正在运行
2. 检查配置文件中的 `server_url` 是否正确
3. 检查是否有防火墙阻止了连接

### 音频设备问题

如果NexTalk无法捕获音频：

1. 确保麦克风已正确连接并工作正常（可以使用系统声音设置测试）
2. 重启NexTalk客户端
3. 如果仍然有问题，检查系统音频驱动是否正常工作

### 识别精度问题

如果语音识别不准确：

1. 尝试使用更大的模型（如从 tiny.en 切换到 small.en）
2. 确保环境噪音较少
3. 讲话清晰并避免过快语速
4. 对于中文识别，切换到 base.zh 模型以获得更好的中文支持

### GPU相关问题

如果您使用GPU加速但遇到问题：

1. 确保已安装正确的CUDA版本（根据faster-whisper要求）
2. 检查GPU驱动是否为最新版本
3. 如果GPU内存不足，尝试使用更小的模型或切换到CPU模式
   - 在 `~/.config/nextalk/config.ini` 中将 `device` 设置为 `cpu`

### 文本注入问题

如果识别正常但文本没有输入到应用程序：

1. 确保已安装 `xdotool`（Linux系统）
2. 检查目标应用程序是否接受键盘输入
3. 尝试在不同的应用程序中测试

### 日志检查

如果遇到其他问题，您可以检查日志获取更多信息：

```bash
# 运行客户端时重定向输出到日志文件
python -m nextalk_client.main > client_log.txt 2>&1
```

或者：

```bash
# 设置更详细的日志级别
export PYTHONPATH=./src
python -m nextalk_client.main --debug
```

## 高级功能

### 多语言支持

NexTalk主要支持英语识别，但也可以通过切换模型来支持其他语言：

1. 在配置文件中设置 `language` 选项（例如 `zh` 表示中文）
2. 使用适当的模型（例如 `base.zh` 用于中文识别）

### 性能调优

对于性能优化，您可以：

1. 调整VAD敏感度（在服务器配置中设置 `vad_sensitivity`，值为1-3，默认为2）
2. 使用适合您硬件的计算精度（在服务器配置中设置 `compute_type`，可选 `int8`、`float16` 或 `float32`）

## 其他资源

- 安装指南：查看 [setup_guide.md](setup_guide.md) 获取完整的安装说明
- 项目架构：查看 [architecture.md](architecture.md)（即将发布）了解NexTalk的技术架构
- 贡献指南：查看 [developer_guide.md](developer_guide.md)（即将发布）了解如何参与项目开发 