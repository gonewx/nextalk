# NexTalk服务器重构计划

## 目录

- [问题分析](#问题分析)
- [重构目标](#重构目标)
- [架构优化方案](#架构优化方案)
- [实施步骤](#实施步骤)
- [进度跟踪](#进度跟踪)

## 问题分析

经过多次迭代，NexTalk服务器代码面临以下问题：

1. **模块耦合度高**：模型管理、WebSocket处理和音频处理逻辑存在较强耦合
2. **代码冗余**：WebSocket和FunASR WebSocket接口存在重复代码
3. **状态管理复杂**：全局单例模式（如`_model_manager_instance`）可能导致状态管理不透明
4. **异常处理不完善**：缺乏统一的错误处理策略，尤其是在模型加载和WebSocket通信中
5. **配置管理分散**：配置参数分散在多个地方（环境变量、命令行、配置文件）
6. **扩展性受限**：当前设计不易添加新的语音识别后端或前端接口

## 重构目标

1. **降低耦合度**：实现更清晰的模块边界和依赖关系
2. **提高代码复用**：消除冗余代码，实现更高效的代码组织
3. **增强异常处理**：统一错误处理策略，提高系统稳定性
4. **调整配置管理**：由之前客户端发送配置管理，改为服务端通过配置文件管理配置
5. **提高扩展性**：支持更多的语音识别后端和前端接口
6. **简化架构**：服务端与客户端的通信只接收音频，然后返回转录结果。旧有涉及其他与客户端的交互功能，全部移除
7. **统一路由**：将所有路由统一到`/ws`路径下，因为server启动时根据配置文件的配置，决定启动哪些功能，所以需要一个统一的路由来处理所有请求。不再使用`/ws/funasr`、`/ws/whisper`等路由。
   
## 架构优化方案

### 1. 依赖注入架构

使用依赖注入模式替代全局单例模式，通过FastAPI的依赖注入系统管理服务组件。

```python
# 依赖注入示例
def get_model_manager():
    # 返回模型管理器实例
    
@app.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket, 
    model_manager: ModelManager = Depends(get_model_manager)
):
    # 使用注入的模型管理器
```

### 2. 统一接口设计

为各类语音识别引擎定义更规范的接口，简化集成新模型的过程。

```python
class ASRBackend(Protocol):
    async def initialize(self) -> bool: ...
    async def transcribe(self, audio: np.ndarray) -> str: ...
    async def reset(self) -> None: ...
```

### 3. 中间件架构

引入中间件架构处理WebSocket连接的生命周期和错误处理。

```python
@app.middleware("websocket")
async def websocket_middleware(websocket: WebSocket, call_next):
    try:
        # 连接计数等
        return await call_next(websocket)
    except Exception as e:
        # 统一错误处理
```

## 实施步骤

### 阶段1：基础结构重构（1-2周）

1. **规范模块边界**
   - [x] 1.1 重构`models`包，实现更清晰的接口设计
   - [x] 1.2 重构`api`包，分离WebSocket处理逻辑和业务逻辑
   - [x] 1.3 实现统一的配置管理模块

2. **优化依赖管理**
   - [x] 2.1 实现依赖注入容器
   - [ ] 2.2 重构服务初始化和组件管理
   - [ ] 2.3 移除全局单例模式

3. **统一错误处理**
   - [ ] 3.1 设计异常层次结构
   - [ ] 3.2 实现统一的错误处理中间件
   - [ ] 3.3 标准化错误响应格式

### 阶段2：核心功能重构（2-3周）

4. **模型管理重构**
   - [ ] 4.1 实现ASR模型Provider接口
   - [ ] 4.2 重构WhisperRecognizer和FunASRRecognizer为Provider实现
   - [ ] 4.3 实现基于工厂模式的模型实例化
   - [ ] 4.4 优化模型资源管理和内存回收

5. **WebSocket接口重构**
   - [ ] 5.1 合并`websocket.py`和`funasr_websocket.py`
   - [ ] 5.2 实现通用WebSocket连接管理器
   - [ ] 5.3 分离连接处理和业务逻辑
   - [ ] 5.4 实现基于会话的状态管理

6. **音频处理流水线重构**
   - [ ] 6.1 设计可组合的音频处理管道
   - [ ] 6.2 实现基于函数式编程的处理链
   - [ ] 6.3 优化VAD与ASR的集成
   - [ ] 6.4 实现可配置的音频处理策略

### 阶段3: 代码文件清理

7. **代码文件清理**
   - [ ] 7.1 移除未使用的文件和代码
   - [ ] 7.2 更新README和文档

### 阶段4：高级特性和优化（2-3周）

8. **扩展功能**
   - [ ] 8.1 完善日志记录和诊断功能

9. **测试和文档**
   - [ ] 9.1 增加单元测试覆盖率
   - [ ] 9.2 实现集成测试套件
   - [ ] 9.3 完善API文档
   - [ ] 9.4 更新架构和开发文档

### 阶段5：最终整合和发布（1-2周）

10. **整合和测试**
    - [ ] 10.1 全面测试与现有客户端的兼容性
    - [ ] 10.2 进行端到端测试

11. **发布准备**
    - [ ] 11.1 更新安装和部署脚本
    - [ ] 11.2 完善用户文档

## 具体实现示例

### 依赖注入容器示例

```python
from fastapi import Depends, FastAPI
from typing import Callable, Dict, Type, TypeVar, Any

T = TypeVar('T')

class Container:
    """依赖注入容器"""
    
    def __init__(self):
        self._providers: Dict[Type, Callable[[], Any]] = {}
        
    def register(self, interface: Type[T], provider: Callable[[], T]) -> None:
        """注册服务提供者"""
        self._providers[interface] = provider
        
    def get(self, interface: Type[T]) -> T:
        """获取服务实例"""
        if interface not in self._providers:
            raise ValueError(f"No provider registered for {interface}")
        return self._providers[interface]()

# 创建容器实例
container = Container()

# 注册服务
container.register(ModelManager, lambda: ModelManager())

# FastAPI依赖
def get_model_manager():
    return container.get(ModelManager)

app = FastAPI()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, model_manager: ModelManager = Depends(get_model_manager)):
    # 使用注入的模型管理器
    pass
```

### 模型提供者接口示例

```python
from abc import ABC, abstractmethod
import numpy as np
from typing import Dict, Any, Optional

class ModelProvider(ABC):
    """模型提供者抽象基类"""
    
    @abstractmethod
    async def initialize(self, config: Dict[str, Any]) -> bool:
        """初始化模型"""
        pass
        
    @abstractmethod
    async def transcribe(self, audio: np.ndarray) -> str:
        """执行转录"""
        pass
        
    @abstractmethod
    async def reset(self) -> None:
        """重置模型状态"""
        pass
        
    @abstractmethod
    async def release(self) -> None:
        """释放模型资源"""
        pass

class WhisperModelProvider(ModelProvider):
    """Whisper模型提供者实现"""
    
    async def initialize(self, config: Dict[str, Any]) -> bool:
        # 实现Whisper模型初始化
        pass
        
    async def transcribe(self, audio: np.ndarray) -> str:
        # 实现Whisper转录
        pass
        
    async def reset(self) -> None:
        # 实现状态重置
        pass
        
    async def release(self) -> None:
        # 实现资源释放
        pass

class ModelFactory:
    """模型工厂"""
    
    _providers = {
        "whisper": WhisperModelProvider,
        "funasr": FunASRModelProvider,
    }
    
    @classmethod
    def create(cls, provider_type: str, config: Dict[str, Any]) -> Optional[ModelProvider]:
        """创建模型提供者实例"""
        if provider_type not in cls._providers:
            return None
            
        provider_class = cls._providers[provider_type]
        provider = provider_class()
        asyncio.create_task(provider.initialize(config))
        return provider
```

## 进度跟踪

### 已完成任务

#### 1. 基础结构重构
- [x] **1.1 重构`models`包，实现更清晰的接口设计** (2023-08-15)
  - 实现了Model接口，定义了语音识别模型的标准接口
  - 分离了Whisper和FunASR模型的实现
  - 统一了模型的初始化、转录和释放流程

- [x] **1.2 重构`api`包，分离WebSocket处理逻辑和业务逻辑** (2023-08-20)
  - 创建了WebSocket处理器基类`BaseWebSocketHandler`，统一处理连接生命周期
  - 实现了WebSocket连接管理器`ConnectionManager`，负责管理活动的WebSocket连接
  - 创建了统一的WebSocket处理器`UnifiedWebSocketHandler`，处理所有ASR请求
  - 创建了ASR服务类`ASRService`，将业务逻辑与WebSocket处理分离
  - 实现了统一的WebSocket路由`/ws`，替代原有的多个WebSocket路由
  - 保留了原有路由以保证兼容性
  - 完成了WebSocket处理器与业务逻辑的解耦，提高了代码复用性和可维护性

- [x] **1.3 实现统一的配置管理模块** (2023-08-16)
  - 创建新的`ConfigManager`类，负责配置的加载和管理
  - 实现了从多个来源加载配置的功能（环境变量、配置文件）
  - 提供了配置的动态更新和保存功能
  - 使用依赖注入模式替代全局单例
  - 更新相关代码以使用新的配置管理模块
  - 实现了服务端通过配置文件管理配置的目标

#### 2. 依赖管理优化
- [x] **2.1 实现依赖注入容器** (2023-08-30)
  - 创建了`Container`类，实现了依赖注入容器的核心功能
  - 实现了服务提供者注册和解析机制
  - 创建了与FastAPI依赖注入系统的集成
  - 创建了常用服务（如ConfigManager和ModelManager）的提供者
  - 更新了WebSocket路由和控制API，使用依赖注入获取服务
  - 重构了服务器应用初始化流程，使用容器管理所有服务组件

#### 7. 代码文件清理
- [x] **7.1 移除未使用的文件和代码** (2023-08-25)
  - 删除了旧的WebSocket实现文件 `websocket.py` 和 `funasr_websocket.py`
  - 移除了server_app.py中对旧WebSocket路由的引用和注册
  - 删除了控制API模块 `control.py`，符合简化架构的要求
  - 更新API包的初始化文件，移除对旧WebSocket模块和控制API的导入
  - 修复了统一WebSocket路由模块中的导入路径
  - 清理了兼容性代码，完全迁移到新的统一WebSocket处理器架构
  - 符合重构目标中"简化架构"的要求，服务端只接收音频并返回转录结果

### 下一步任务
- [ ] **2.2 重构服务初始化和组件管理**
  - 应用生命周期管理
  - 异步服务初始化
  - 组件间依赖管理
- [ ] **7.2 更新README和文档**
  - 更新服务器文档，反映最新的架构和API
  - 更新README文件，说明安装和使用方法
  - 添加依赖注入容器的使用说明
