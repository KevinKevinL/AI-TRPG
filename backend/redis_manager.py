# redis_manager.py
"""
Redis连接管理模块
提供全局的Redis客户端访问
"""

import redis
import os
from typing import Optional

class RedisManager:
    """Redis连接管理器"""
    
    def __init__(self):
        self._client: Optional[redis.Redis] = None
        self._is_connected = False
    
    def initialize(self, host: str = None, port: int = None, db: int = None):
        """初始化Redis连接"""
        try:
            # 从环境变量获取配置，如果没有则使用默认值
            redis_host = host or os.getenv("REDIS_HOST", "localhost")
            redis_port = port or int(os.getenv("REDIS_PORT", 6379))
            redis_db = db or int(os.getenv("REDIS_DB", 0))
            
            # 建立Redis连接
            self._client = redis.Redis(
                host=redis_host, 
                port=redis_port, 
                db=redis_db, 
                decode_responses=True
            )
            
            # 测试连接
            self._client.ping()
            self._is_connected = True
            print(f"✅ Redis连接成功！主机: {redis_host}:{redis_port}, 数据库: {redis_db}")
            
        except Exception as e:
            print(f"❌ Redis连接失败: {e}")
            self._client = None
            self._is_connected = False
    
    def get_client(self) -> Optional[redis.Redis]:
        """获取Redis客户端实例"""
        return self._client if self._is_connected else None
    
    def is_connected(self) -> bool:
        """检查Redis是否已连接"""
        if not self._client or not self._is_connected:
            return False
        try:
            self._client.ping()
            return True
        except:
            self._is_connected = False
            return False
    
    def close(self):
        """关闭Redis连接"""
        if self._client:
            try:
                self._client.close()
                self._is_connected = False
                print("✅ Redis连接已关闭")
            except Exception as e:
                print(f"❌ 关闭Redis连接时出错: {e}")

# 创建全局Redis管理器实例
redis_manager = RedisManager()

def get_redis_client() -> Optional[redis.Redis]:
    """获取Redis客户端的便捷函数"""
    return redis_manager.get_client()

def is_redis_connected() -> bool:
    """检查Redis连接状态的便捷函数"""
    return redis_manager.is_connected()
