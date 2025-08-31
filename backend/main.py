# main.py
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from contextlib import asynccontextmanager
from dotenv import load_dotenv
import os
import json
from typing import List

# 从其他文件导入路由器
from graph import graph_router
from background import background_router
from character import character_router
from redis_manager import redis_manager, save_world_state
from databaseManager import db_manager
from player_action_parser import add_websocket_connection, remove_websocket_connection

load_dotenv()

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

manager = ConnectionManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    redis_manager.initialize()
    # --- 新增：加载世界状态到Redis ---
    if redis_manager.is_connected():
        initial_world_state = db_manager.get_initial_world_state()
        save_world_state(initial_world_state)
        print("初始世界状态已加载到Redis。")
    
    yield
    # 关闭时执行
    redis_manager.close()

app = FastAPI(lifespan=lifespan)

app.include_router(graph_router, prefix="/api")
app.include_router(background_router, prefix="/api")
app.include_router(character_router, prefix="/api")

# 调试：打印所有注册的路由
print("=== 已注册的路由 ===")
for route in app.routes:
    if hasattr(route, 'path'):
        print(f"路由: {route.path} [{', '.join(route.methods)}]")
print("==================")

@app.get("/")
def read_root():
    return {"message": "Welcome to the CoC AI Backend!"}

@app.get("/health")
def health_check():
    redis_status = "connected" if redis_manager.is_connected() else "disconnected"
    return {"status": "healthy", "redis": redis_status}

@app.websocket("/ws/dice")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text() # 保持连接
    except WebSocketDisconnect:
        manager.disconnect(websocket)
