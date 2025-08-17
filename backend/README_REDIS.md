# Redis管理架构说明

## 概述

本项目已将Redis连接管理重构为集中式管理，所有Redis操作都通过统一的`redis_manager`模块进行。

## 架构变化

### 之前的问题
- 每个模块都单独初始化Redis连接
- 代码重复，难以维护
- 连接状态管理分散

### 现在的解决方案
- 在`main.py`启动时统一初始化Redis连接
- 通过`redis_manager`模块提供全局访问
- 应用关闭时自动清理连接

## 文件结构

```
backend/
├── main.py              # 主应用入口，负责Redis初始化
├── redis_manager.py     # Redis连接管理器
├── graph.py            # 使用Redis管理器的模块示例
└── test_redis_manager.py # Redis管理器测试脚本
```

## 使用方法

### 1. 在main.py中
```python
from redis_manager import redis_manager

@app.on_event("startup")
async def startup_event():
    """应用启动时执行的事件"""
    # 初始化Redis连接
    redis_manager.initialize()

@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时执行的事件"""
    # 关闭Redis连接
    redis_manager.close()
```

### 2. 在其他模块中
```python
from redis_manager import get_redis_client, is_redis_connected

def some_function():
    # 获取Redis客户端
    redis_client = get_redis_client()
    
    if redis_client:
        # 执行Redis操作
        redis_client.set("key", "value")
    else:
        print("Redis客户端不可用")
```

## 环境变量配置

可以在`.env`文件中配置Redis连接参数：

```env
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
```

如果不设置，将使用默认值：
- 主机：localhost
- 端口：6379
- 数据库：0

## 健康检查

新增了健康检查端点`/health`，可以检查Redis连接状态：

```bash
curl http://localhost:8000/health
```

响应示例：
```json
{
    "status": "healthy",
    "redis": "connected",
    "message": "CoC AI Backend is running"
}
```

## 测试

运行测试脚本验证Redis管理器：

```bash
cd backend
python test_redis_manager.py
```

## 优势

1. **集中管理**：所有Redis连接在一个地方管理
2. **自动清理**：应用关闭时自动关闭连接
3. **错误处理**：统一的错误处理和日志记录
4. **配置灵活**：支持环境变量配置
5. **状态监控**：可以随时检查连接状态
6. **避免循环导入**：使用专门的模块避免循环导入问题

## 注意事项

1. 确保Redis服务器正在运行
2. 检查防火墙设置，确保可以连接到Redis端口
3. 如果Redis连接失败，应用仍会启动，但相关功能可能不可用
4. 所有Redis操作都应该检查客户端是否可用
