# main.py
from fastapi import FastAPI
from dotenv import load_dotenv

# 从其他文件导入路由器
from graph import graph_router
from background import background_router
from character import character_router

# 加载环境变量
load_dotenv()

# 创建主 FastAPI 应用实例
app = FastAPI()

# 使用 include_router 将不同的功能模块的路由加载到主应用中
# 这样就可以通过一个服务器来管理所有的 API
app.include_router(graph_router, prefix="/api")
app.include_router(background_router, prefix="/api")
app.include_router(character_router, prefix="/api")

@app.get("/")
def read_root():
    return {"message": "Welcome to the CoC AI Backend!"}

