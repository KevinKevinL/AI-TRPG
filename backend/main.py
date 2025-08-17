# main.py
from fastapi import FastAPI
from contextlib import asynccontextmanager
from dotenv import load_dotenv
import os

# 从其他文件导入路由器
from graph import graph_router
from background import background_router
from character import character_router
from redis_manager import redis_manager

# 加载环境变量
load_dotenv()

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

