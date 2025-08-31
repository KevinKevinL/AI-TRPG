redis下载：
windows https://github.com/redis-windows/redis-windows
图形化客户端 https://github.com/lework/RedisDesktopManager-Windows/releases

redis启动设置：
默认port=6379就行
命令行运行：
redis-server.exe redis.conf

redis连接端口配置：
可以在`.env`文件中配置Redis连接参数
如果不设置，将使用默认值：
- 主机：localhost
- 端口：6379
- 数据库：0

运行以下命令可以检查Redis连接状态：
```bash
curl http://localhost:8000/health
```

前端启动：
根目录下
npm install
npm run dev

后端启动：
backend目录下
uvicorn main:app --reload --port 8000

记忆管理：
backend目录下
python chroma_interactive.py



