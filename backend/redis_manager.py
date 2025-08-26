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
                "character_hit_points": status.get("hit_points", 10),
                "character_magic_points": status.get("magic_points", 10),
                "happening_event_id": status.get("happening_event_id", -1),  # 当前正在进行的事件ID
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
        "character_hit_points": 10,
        "character_magic_points": 10,
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

def update_happening_event_id_in_redis(character_id: str, happening_event_id: int):
    """更新Redis中角色的当前事件ID"""
    try:
        redis_client = get_redis_client()
        if not redis_client:
            print("Redis客户端不可用，无法更新事件ID")
            return False
            
        # 获取当前状态数据
        status_key = f"character_status:{character_id}"
        status_data = redis_client.get(status_key)
        
        if status_data:
            status = json.loads(status_data)
            # 更新事件ID
            status["happening_event_id"] = happening_event_id
            
            # 保存回Redis
            redis_client.setex(status_key, 86400, json.dumps(status, ensure_ascii=False))
            print(f"角色 {character_id} 的事件ID已更新为: {happening_event_id}")
            return True
        else:
            print(f"Redis中未找到角色 {character_id} 的状态数据")
            return False
            
    except Exception as e:
        print(f"更新事件ID失败: {e}")
        return False

def clean_invalid_event_data(character_id: str):
    """清理Redis中无效的事件数据"""
    try:
        redis_client = get_redis_client()
        if not redis_client:
            print("Redis客户端不可用，无法清理事件数据")
            return False
            
        # 清理已完成事件ID列表中的无效值
        ids_key = f"completed_event_ids:{character_id}"
        ids_data = redis_client.get(ids_key)
        if ids_data:
            try:
                event_ids = json.loads(ids_data)
                # 过滤掉无效的事件ID（<=0）
                valid_event_ids = [eid for eid in event_ids if isinstance(eid, int) and eid > 0]
                if len(valid_event_ids) != len(event_ids):
                    redis_client.setex(ids_key, 86400, json.dumps(valid_event_ids))
                    print(f"已清理无效事件ID，从 {len(event_ids)} 个清理到 {len(valid_event_ids)} 个")
            except json.JSONDecodeError:
                print(f"事件ID数据格式错误，重置为空列表")
                redis_client.setex(ids_key, 86400, json.dumps([]))
        
        # 清理已完成事件列表中的无效值
        events_key = f"completed_events:{character_id}"
        events_data = redis_client.get(events_key)
        if events_data:
            try:
                events = json.loads(events_data)
                # 过滤掉"未知事件"等无效描述
                valid_events = [event for event in events if event and event != "未知事件" and event != "分支出错，正在发生的事件无检定"]
                if len(valid_events) != len(events):
                    redis_client.setex(events_key, 86400, json.dumps(valid_events))
                    print(f"已清理无效事件描述，从 {len(events)} 个清理到 {len(valid_events)} 个")
            except json.JSONDecodeError:
                print(f"事件描述数据格式错误，重置为空列表")
                redis_client.setex(events_key, 86400, json.dumps([]))
        
        return True
        
    except Exception as e:
        print(f"清理事件数据失败: {e}")
        return False



def update_character_attribute_by_id(character_id: str, attribute_changes: List[tuple]):
    """
    根据属性ID更新角色在Redis中的属性值
    
    Args:
        character_id: 角色ID
        attribute_changes: 属性变化列表，每个元素为 (attribute_id, change_value)
                          例如: [(10, -2), (13, -1)] 表示理智值-2，生命值-1
    
    Returns:
        bool: 更新是否成功
    """
    try:
        redis_client = get_redis_client()
        if not redis_client:
            print("Redis客户端不可用，无法更新角色属性")
            return False
            
        # 获取当前角色数据
        character_key = f"character_data:{character_id}"
        status_key = f"character_status:{character_id}"
        
        character_data = redis_client.get(character_key)
        status_data = redis_client.get(status_key)
        
        if not character_data or not status_data:
            print(f"Redis中未找到角色 {character_id} 的完整数据")
            return False
            
        character = json.loads(character_data)
        status = json.loads(status_data)
        
        # 属性ID到字段名的映射 - 使用 skillCheck.py 中的映射
        from skillCheck import get_attribute_field_mapping
        
        attribute_field_mapping = get_attribute_field_mapping()
        
        updated_attributes = []
        
        for attribute_id, change_value in attribute_changes:
            if attribute_id not in attribute_field_mapping:
                print(f"未知的属性ID: {attribute_id}")
                continue
                
            data_type, field_name = attribute_field_mapping[attribute_id]
            
            if data_type == "attributes":
                # 更新基础属性
                current_value = character.get("attributes", {}).get(field_name, 0)
                new_value = max(0, current_value + change_value)  # 属性值不能低于0
                character["attributes"][field_name] = new_value
                updated_attributes.append(f"{field_name}: {current_value} -> {new_value} ({change_value:+d})")
                
            elif data_type == "status":
                # 更新状态属性
                current_value = status.get(field_name, 0)
                new_value = max(0, current_value + change_value)  # 状态值不能低于0
                status[field_name] = new_value
                updated_attributes.append(f"{field_name}: {current_value} -> {new_value} ({change_value:+d})")
                
            elif data_type == "skills":
                # 更新技能值
                current_value = character.get("skills", {}).get(field_name, 0)
                new_value = max(0, current_value + change_value)  # 技能值不能低于0
                character["skills"][field_name] = new_value
                updated_attributes.append(f"{field_name}: {current_value} -> {new_value} ({change_value:+d})")
        
        if updated_attributes:
            # 保存更新后的数据
            redis_client.setex(character_key, 86400, json.dumps(character, ensure_ascii=False))
            redis_client.setex(status_key, 86400, json.dumps(status, ensure_ascii=False))
            
            print(f"角色 {character_id} 属性已更新: {', '.join(updated_attributes)}")
            return True
        else:
            print(f"没有需要更新的属性")
            return True
            
    except Exception as e:
        print(f"更新角色属性失败: {e}")
        return False

def get_character_status_from_redis(character_id: str) -> Dict[str, Any]:
    """
    从Redis获取角色状态数据
    
    Args:
        character_id: 角色ID
    
    Returns:
        Dict: 角色状态数据，包含hit_points、sanity等字段
    """
    try:
        redis_client = get_redis_client()
        if not redis_client:
            print("Redis客户端不可用，返回默认状态")
            return {"hit_points": 10, "sanity": 99, "magic_points": 10}
            
        status_key = f"character_status:{character_id}"
        status_data = redis_client.get(status_key)
        
        if status_data:
            return json.loads(status_data)
        else:
            print(f"Redis中未找到角色 {character_id} 的状态数据，返回默认值")
            return {"hit_points": 10, "sanity": 99, "magic_points": 10}
            
    except Exception as e:
        print(f"获取角色状态失败: {e}")
        return {"hit_points": 10, "sanity": 99, "magic_points": 10}
