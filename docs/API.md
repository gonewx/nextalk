# NexTalk API 文档

本文档描述了 NexTalk 的核心 API 接口，供开发者集成和扩展使用。

## 目录

- [核心模块](#核心模块)
- [音频处理](#音频处理)
- [网络通信](#网络通信)
- [输入控制](#输入控制)
- [输出处理](#输出处理)
- [配置管理](#配置管理)
- [事件系统](#事件系统)

## 核心模块

### MainController

主控制器，协调所有模块的工作。

```python
from nextalk.core.controller import MainController

# 创建控制器实例
controller = MainController(config_path="config/nextalk.yaml")

# 启动系统
await controller.start()

# 停止系统
await controller.stop()

# 获取状态
status = controller.get_status()
```

### Session

会话管理器，处理语音识别会话。

```python
from nextalk.core.session import Session

# 创建会话
session = Session(session_id="unique_id")

# 开始会话
session.start()

# 添加音频数据
session.add_audio(audio_data)

# 获取识别结果
result = session.get_result()

# 结束会话
session.end()
```

## 音频处理

### AudioCaptureManager

音频采集管理器。

```python
from nextalk.audio.capture import AudioCaptureManager

# 创建采集器
capture = AudioCaptureManager(
    sample_rate=16000,
    channels=1,
    chunk_size=1024
)

# 设置回调函数
def on_audio_data(data):
    print(f"接收到音频数据: {len(data)} 字节")

capture.set_callback(on_audio_data)

# 开始采集
capture.start_capture()

# 停止采集
capture.stop_capture()

# 获取设备列表
devices = capture.list_devices()
```

### AudioDevice

音频设备管理。

```python
from nextalk.audio.device import AudioDevice

# 获取默认设备
device = AudioDevice.get_default_input()

# 列出所有设备
devices = AudioDevice.list_all()

# 选择特定设备
device = AudioDevice.get_by_name("Microphone")

# 获取设备信息
info = device.get_info()
```

## 网络通信

### WebSocketClient

WebSocket 客户端。

```python
from nextalk.network.ws_client import WebSocketClient

# 创建客户端
client = WebSocketClient(
    url="ws://localhost:10095",
    auto_reconnect=True
)

# 设置事件处理器
@client.on("message")
async def on_message(data):
    print(f"收到消息: {data}")

@client.on("error")
async def on_error(error):
    print(f"错误: {error}")

# 连接服务器
await client.connect()

# 发送消息
await client.send({
    "type": "audio",
    "data": audio_data
})

# 断开连接
await client.disconnect()
```

### Protocol

通信协议处理。

```python
from nextalk.network.protocol import Protocol

# 创建消息
message = Protocol.create_message(
    msg_type="audio",
    data=audio_data,
    metadata={"sample_rate": 16000}
)

# 解析消息
parsed = Protocol.parse_message(raw_message)

# 验证消息
is_valid = Protocol.validate_message(message)
```

## 输入控制

### HotkeyManager

全局快捷键管理。

```python
from nextalk.input.hotkey import HotkeyManager

# 创建管理器
hotkey = HotkeyManager()

# 注册快捷键
hotkey.register(
    key_combination="ctrl+alt+space",
    callback=lambda: print("快捷键被按下")
)

# 注销快捷键
hotkey.unregister("ctrl+alt+space")

# 启动监听
hotkey.start_listening()

# 停止监听
hotkey.stop_listening()

# 获取已注册的快捷键
registered = hotkey.get_registered_hotkeys()
```

### KeyListener

键盘事件监听器。

```python
from nextalk.input.listener import KeyListener

# 创建监听器
listener = KeyListener()

# 设置事件处理器
@listener.on_key_press
def on_press(key):
    print(f"按键按下: {key}")

@listener.on_key_release
def on_release(key):
    print(f"按键释放: {key}")

# 启动监听
listener.start()

# 停止监听
listener.stop()
```

## 输出处理

### TextInjector

文本注入器。

```python
from nextalk.output.text_injector import TextInjector

# 创建注入器
injector = TextInjector()

# 注入文本到当前光标位置
injector.inject_text("Hello, World!")

# 注入带格式的文本
injector.inject_formatted(
    text="格式化文本",
    format="markdown"
)

# 获取当前应用信息
app_info = injector.get_active_application()

# 设置注入选项
injector.set_options({
    "delay": 0.01,  # 字符间延迟
    "use_clipboard": False  # 是否使用剪贴板
})
```

### ClipboardManager

剪贴板管理。

```python
from nextalk.output.clipboard import ClipboardManager

# 创建管理器
clipboard = ClipboardManager()

# 保存当前剪贴板
saved = clipboard.save_current()

# 设置剪贴板内容
clipboard.set_text("新内容")

# 获取剪贴板内容
content = clipboard.get_text()

# 恢复剪贴板
clipboard.restore(saved)

# 清空剪贴板
clipboard.clear()
```

## 配置管理

### ConfigManager

配置管理器。

```python
from nextalk.config.manager import ConfigManager

# 加载配置
config = ConfigManager.load("config/nextalk.yaml")

# 获取配置值
server_host = config.get("server.host", default="localhost")

# 设置配置值
config.set("audio.sample_rate", 16000)

# 保存配置
config.save()

# 验证配置
is_valid = config.validate()

# 重置为默认值
config.reset_to_defaults()
```

### NexTalkConfig

配置数据模型。

```python
from nextalk.config.models import NexTalkConfig

# 创建配置实例
config = NexTalkConfig(
    server_host="localhost",
    server_port=10095,
    audio_device="default"
)

# 转换为字典
config_dict = config.to_dict()

# 从字典创建
config = NexTalkConfig.from_dict(config_dict)

# 验证配置
config.validate()
```

## 事件系统

### EventEmitter

事件发射器基类。

```python
from nextalk.utils.events import EventEmitter

class MyClass(EventEmitter):
    def __init__(self):
        super().__init__()
    
    def do_something(self):
        # 触发事件
        self.emit("something_done", data="result")

# 使用
obj = MyClass()

# 监听事件
@obj.on("something_done")
def handler(data):
    print(f"事件触发: {data}")

# 触发
obj.do_something()

# 移除监听器
obj.off("something_done", handler)

# 一次性监听
@obj.once("special_event")
def one_time_handler(data):
    print("只执行一次")
```

## 工具函数

### Logger

日志工具。

```python
from nextalk.utils.logger import get_logger

# 获取日志器
logger = get_logger(__name__)

# 记录日志
logger.debug("调试信息")
logger.info("普通信息")
logger.warning("警告信息")
logger.error("错误信息")
logger.critical("严重错误")

# 设置日志级别
logger.set_level("DEBUG")
```

### Monitor

性能监控。

```python
from nextalk.utils.monitor import Monitor

# 创建监控器
monitor = Monitor()

# 开始监控
monitor.start()

# 获取指标
metrics = monitor.get_metrics()
print(f"CPU: {metrics['cpu_percent']}%")
print(f"内存: {metrics['memory_mb']} MB")

# 停止监控
monitor.stop()

# 使用装饰器监控函数性能
@monitor.measure
def my_function():
    # 函数逻辑
    pass
```

## 扩展开发

### 创建插件

```python
from nextalk.plugin import Plugin

class MyPlugin(Plugin):
    """自定义插件示例"""
    
    def __init__(self):
        super().__init__(
            name="my_plugin",
            version="1.0.0"
        )
    
    def on_load(self):
        """插件加载时调用"""
        print("插件已加载")
    
    def on_audio_captured(self, audio_data):
        """音频采集时调用"""
        # 处理音频数据
        processed = self.process_audio(audio_data)
        return processed
    
    def on_text_recognized(self, text):
        """文本识别后调用"""
        # 处理识别结果
        modified = text.upper()
        return modified
    
    def on_unload(self):
        """插件卸载时调用"""
        print("插件已卸载")

# 注册插件
from nextalk.plugin_manager import PluginManager

manager = PluginManager()
manager.register(MyPlugin())
```

### 自定义音频处理器

```python
from nextalk.audio.processor import AudioProcessor

class NoiseReducer(AudioProcessor):
    """噪声抑制处理器"""
    
    def process(self, audio_data):
        # 实现噪声抑制算法
        reduced = self.reduce_noise(audio_data)
        return reduced
    
    def reduce_noise(self, data):
        # 具体实现
        pass

# 使用
reducer = NoiseReducer()
clean_audio = reducer.process(noisy_audio)
```

## 错误处理

```python
from nextalk.exceptions import (
    NexTalkException,
    AudioException,
    NetworkException,
    ConfigException
)

try:
    # 可能出错的代码
    controller.start()
except AudioException as e:
    print(f"音频错误: {e}")
except NetworkException as e:
    print(f"网络错误: {e}")
except ConfigException as e:
    print(f"配置错误: {e}")
except NexTalkException as e:
    print(f"通用错误: {e}")
```

## 异步编程

NexTalk 使用 asyncio 进行异步编程：

```python
import asyncio
from nextalk.core.controller import MainController

async def main():
    controller = MainController()
    
    try:
        # 异步启动
        await controller.start()
        
        # 等待用户输入
        await asyncio.sleep(60)
        
    finally:
        # 异步停止
        await controller.stop()

# 运行
asyncio.run(main())
```

## 最佳实践

1. **资源管理**：始终使用 try-finally 或 context manager 确保资源正确释放
2. **错误处理**：捕获并适当处理所有异常
3. **异步编程**：使用 async/await 处理 I/O 密集操作
4. **日志记录**：记录关键操作和错误信息
5. **配置管理**：使用配置文件而不是硬编码值
6. **事件驱动**：使用事件系统解耦模块
7. **性能监控**：定期监控系统性能指标

## 更多信息

- [架构设计](ARCHITECTURE.md)
- [贡献指南](../CONTRIBUTING.md)
- [常见问题](FAQ.md)
- [示例代码](examples/)