# redis_manager.py
"""
Redis连接管理模块
提供全局的Redis客户端访问和角色数据管理
"""

import redis
import os
import json
from typing import Optional, Dict, Any, List

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

# --- 角色数据管理函数 ---

def get_character_data_from_redis(character_id: str) -> Dict[str, Any]:
    """从Redis获取角色数据"""
    try:
        redis_client = get_redis_client()
        if not redis_client:
            print("Redis客户端不可用，返回默认角色数据")
            return get_default_character_data()
            
        # 获取角色基础数据
        character_key = f"character_data:{character_id}"
        character_data = redis_client.get(character_key)
        
        # 获取角色状态数据
        status_key = f"character_status:{character_id}"
        status_data = redis_client.get(status_key)
        
        if character_data and status_data:
            character = json.loads(character_data)
            status = json.loads(status_data)
            
            # 合并数据
            return {
                "character_info": character.get("info", {}),
                "character_attributes": character.get("attributes", {}),
                "character_skills": character.get("skills", {}),
                "character_derived_attributes": character.get("derived_attributes", {}),
                "character_background": character.get("info", {}).get("background", "未知"),
                "character_profession": character.get("info", {}).get("profession", "未知"),
                "current_location": status.get("current_location", "未知"),
                "current_map_id": status.get("current_map_id", "1"),
                "character_sanity": status.get("sanity", 99),
                "character_health": status.get("health", 10),
                "character_magic": status.get("magic", 10),
                "item_inventory": [],  # 暂时为空，后续可以扩展
                "nearby_objects": [],  # 暂时为空，后续可以扩展
                "npc_presence": []     # 暂时为空，后续可以扩展
            }
        else:
            print(f"Redis中未找到角色 {character_id} 的数据，使用默认数据")
            return get_default_character_data()
            
    except Exception as e:
        print(f"从Redis获取角色数据失败: {e}")
        return get_default_character_data()

def get_default_character_data() -> Dict[str, Any]:
    """获取默认角色数据"""
    return {
        "character_info": {},
        "character_attributes": {},
        "character_skills": {},
        "character_derived_attributes": {},
        "character_background": "未知",
        "character_profession": "未知",
        "current_location": "未知",
        "current_map_id": "1",
        "character_sanity": 99,
        "character_health": 10,
        "character_magic": 10,
        "item_inventory": [],
        "nearby_objects": [],
        "npc_presence": []
    }

def save_character_data_to_redis(character_id: str, character_data: Dict[str, Any], character_status: Dict[str, Any]):
    """保存角色数据到Redis"""
    try:
        redis_client = get_redis_client()
        if not redis_client:
            print("Redis客户端不可用，无法保存角色数据")
            return False
            
        # 保存角色基础数据
        character_key = f"character_data:{character_id}"
        redis_client.setex(character_key, 86400, json.dumps(character_data, ensure_ascii=False))
        
        # 保存角色状态数据
        status_key = f"character_status:{character_id}"
        redis_client.setex(status_key, 86400, json.dumps(character_status, ensure_ascii=False))
        
        print(f"角色 {character_id} 的数据已成功保存到Redis")
        return True
        
    except Exception as e:
        print(f"保存角色数据到Redis失败: {e}")
        return False

def delete_character_data_from_redis(character_id: str):
    """从Redis删除角色数据"""
    try:
        redis_client = get_redis_client()
        if not redis_client:
            print("Redis客户端不可用，无法删除角色数据")
            return False
            
        # 删除角色基础数据
        character_key = f"character_data:{character_id}"
        redis_client.delete(character_key)
        
        # 删除角色状态数据
        status_key = f"character_status:{character_id}"
        redis_client.delete(status_key)
        
        print(f"角色 {character_id} 的数据已从Redis删除")
        return True
        
    except Exception as e:
        print(f"删除角色数据失败: {e}")
        return False
