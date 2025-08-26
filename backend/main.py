# main.py
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from contextlib import asynccontextmanager
from dotenv import load_dotenv
import os
import json
import asyncio
from typing import List

# 从其他文件导入路由器
from graph import graph_router
from background import background_router
from character import character_router
from redis_manager import redis_manager
from skillCheck import skill_check, add_websocket_connection, remove_websocket_connection

# 加载环境变量
load_dotenv()

# WebSocket连接管理器
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        add_websocket_connection(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        remove_websocket_connection(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                pass

manager = ConnectionManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    redis_manager.initialize()
    yield
    # 关闭时执行
    redis_manager.close()

# 创建主 FastAPI 应用实例
app = FastAPI(lifespan=lifespan)

# 使用 include_router 将不同的功能模块的路由加载到主应用中
# 这样就可以通过一个服务器来管理所有的 API
app.include_router(graph_router, prefix="/api")
app.include_router(background_router, prefix="/api")
app.include_router(character_router, prefix="/api")

@app.get("/")
def read_root():
    return {"message": "Welcome to the CoC AI Backend!"}

@app.get("/health")
def health_check():
    """健康检查端点，包括Redis连接状态"""
    redis_status = "connected" if redis_manager.is_connected() else "disconnected"
    return {
        "status": "healthy",
        "redis": redis_status,
        "message": "CoC AI Backend is running"
    }

@app.websocket("/ws/dice")
async def websocket_endpoint(websocket: WebSocket):
    """骰子WebSocket端点"""
    await manager.connect(websocket)
    try:
        while True:
            # 保持连接活跃
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                if message.get('type') == 'ping':
                    await websocket.send_text(json.dumps({'type': 'pong'}))
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"WebSocket错误: {e}")
        manager.disconnect(websocket)

@app.post("/api/skillCheck")
async def skill_check_endpoint(request: dict):
    """技能检定API端点"""
    try:
        player_input = request.get('player_input', '')
        character_id = request.get('character_id')
        
        if not player_input:
            return {"error": "缺少玩家输入"}
        
        # 执行技能检定
        result = skill_check(player_input)
        
        return result
        
    except Exception as e:
        return {"error": f"技能检定失败: {str(e)}"}

