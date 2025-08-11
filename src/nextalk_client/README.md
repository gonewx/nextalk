# NexTalk 客户端

NexTalk客户端是一个轻量级语音识别应用，为您提供实时音频转文本服务。

## 简介

NexTalk客户端通过WebSocket与服务器进行通信，提供以下核心功能：

- **实时音频捕获**：捕获麦克风输入的音频
- **音频传输**：将音频数据发送到服务器
- **文本接收**：接收服务器返回的转录文本
- **文本处理**：将转录文本显示或注入到活动窗口

## 特点

- **简单高效**：专注于核心语音转文本功能
- **热键触发**：通过热键快速启动/停止语音捕获
- **系统托盘**：方便的托盘图标显示应用状态
- **文本注入**：可选择将转录文本直接输入到活动窗口
- **文本显示**：在控制台显示转录文本

## 简化说明

此版本是NexTalk客户端的简化版，进行了以下优化：

- 移除了服务器配置相关功能
- 移除了模型切换功能
- 专注于核心的音频发送和文本接收功能
- 简化了与服务器的通信协议

## 安装与依赖

NexTalk客户端依赖于以下软件和库：

### 系统依赖

- **xdotool**: 用于文本注入（将转录文本输入到当前光标位置）
- **xclip**: 用于剪贴板操作（备用文本注入方法）

### Python依赖

- Python 3.8+
- websockets: 用于WebSocket通信
- numpy: 用于音频处理
- PyAudio: 用于音频捕获
- pynput: 用于热键监听
- Pillow: 用于图像处理

### 快速安装依赖

我们提供了一个依赖检查与安装脚本，可以自动检测并安装所需依赖：

```bash
# 检查依赖并显示安装指令
python3 setup_dependencies.py

# 自动安装缺失的依赖（需要sudo权限）
python3 setup_dependencies.py --auto-install
```

### 手动安装依赖

如果您希望手动安装依赖，可以使用以下命令：

```bash
# 安装系统依赖
sudo apt install xdotool xclip

# 安装Python依赖
pip install websockets numpy pyaudio pynput pillow
```

## 使用方法

1. 启动客户端应用
2. 使用热键（默认为`Ctrl+Shift+Space`）激活语音捕获
3. 说话，您的语音将被转录成文本
4. 再次按下热键停止语音捕获

## 配置

客户端配置位于`~/.config/nextalk/client.ini`，主要配置项包括：

```ini
[Client]
hotkey = ctrl+shift+space
server_url = ws://127.0.0.1:8000/ws/stream
enable_injection = true
show_text = true
```

- `hotkey`: 启动/停止语音捕获的热键组合
- `server_url`: 服务器WebSocket地址
- `enable_injection`: 是否启用文本注入功能
- `show_text`: 是否显示转录文本

## 故障排除

### 文本注入不工作

1. 确保已安装`xdotool`：`sudo apt install xdotool`
2. 检查是否有权限问题：`which xdotool`确认路径，并检查执行权限
3. 尝试手动执行：`xdotool type "测试文本"`

### 音频捕获问题

1. 确保麦克风已正确连接并设置为默认设备
2. 检查音频权限：`pulseaudio --check`和`pulseaudio --start`
3. 安装PyAudio：`pip install pyaudio`和`sudo apt install python3-pyaudio`

## 系统要求

- Linux系统（已在Ubuntu 22.04上测试）
- Python 3.8+
- 依赖库：参见"安装与依赖"部分 