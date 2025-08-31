# redis_manager.py
"""
Redis连接管理模块, 采用'动静分离'原则管理游戏状态
"""
import redis
import os
import json
from typing import Optional, Dict, Any, List

class RedisManager:
    def __init__(self):
        self._client: Optional[redis.Redis] = None
        self._is_connected = False
    
    def initialize(self, host: str = None, port: int = None, db: int = None):
        try:
            redis_host = host or os.getenv("REDIS_HOST", "localhost")
            redis_port = port or int(os.getenv("REDIS_PORT", 6379))
            redis_db = db or int(os.getenv("REDIS_DB", 0))
            
            self._client = redis.Redis(host=redis_host, port=redis_port, db=redis_db, decode_responses=True)
            self._client.ping()
            self._is_connected = True
            print(f"✅ Redis连接成功！主机: {redis_host}:{redis_port}, 数据库: {redis_db}")
        except Exception as e:
            print(f"❌ Redis连接失败: {e}")
            self._client = None
            self._is_connected = False
    
    def get_client(self) -> Optional[redis.Redis]:
        return self._client if self._is_connected else None
    
    def is_connected(self) -> bool:
        return self._is_connected

    def close(self):
        if self._client:
            self._client.close()
            print("Redis连接已关闭。")

# --- 全局实例和便捷函数 ---
redis_manager = RedisManager()
def get_redis_client() -> Optional[redis.Redis]:
    return redis_manager.get_client()

# --- 键名常量 ---
WORLD_STATE_KEY = "world_state"
MAP_STATE_KEY_PREFIX = "map_state:" # 新增
SHEET_KEY_PREFIX = "character_sheet:"
SESSION_KEY_PREFIX = "session_state:"
CONVERSATION_KEY_PREFIX = "conversation_history:"
COMPLETED_EVENTS_KEY_PREFIX = "completed_events:"

# --- 1. 世界状态管理 ---
def save_world_state(state: Dict[str, Any]):
    redis_client = get_redis_client()
    if not redis_client: return
    redis_client.set(WORLD_STATE_KEY, json.dumps(state, ensure_ascii=False))

def get_world_state() -> Dict[str, Any]:
    redis_client = get_redis_client()
    if not redis_client: return {}
    data = redis_client.get(WORLD_STATE_KEY)
    return json.loads(data) if data else {}

# --- 2. 地图状态管理 ---
def save_map_state(map_id: int, map_data: Dict[str, Any]):
    redis_client = get_redis_client()
    if not redis_client: return
    key = f"{MAP_STATE_KEY_PREFIX}{map_id}"
    redis_client.setex(key, 86400, json.dumps(map_data, ensure_ascii=False))

def get_map_state(map_id: int) -> Dict[str, Any]:
    redis_client = get_redis_client()
    if not redis_client: return {"npcs": [], "objects": {}, "accessible_maps": []}
    key = f"{MAP_STATE_KEY_PREFIX}{map_id}"
    data = redis_client.get(key)
    return json.loads(data) if data else {"npcs": [], "objects": {}, "accessible_maps": []}

# --- 2.1. 地图可访问性管理 (集成到map_state中) ---
def get_map_accessibility(map_id: int) -> List[int]:
    """从map_state中获取地图的可访问性信息"""
    map_state = get_map_state(map_id)
    accessible_maps = map_state.get("accessible_maps", [])
    
    # 如果Redis中没有数据，尝试从数据库重新初始化
    if not accessible_maps:
        print(f"地图{map_id}的Redis中没有可访问性数据，尝试重新初始化...")
        initialize_map_accessibility_from_db(map_id)
        # 重新获取
        map_state = get_map_state(map_id)
        accessible_maps = map_state.get("accessible_maps", [])
    
    return accessible_maps

def update_map_accessibility(map_id: int, target_map_id: int, is_accessible: bool):
    """更新特定地图的可访问性"""
    redis_client = get_redis_client()
    if not redis_client: return
    
    # 获取当前地图状态
    map_state = get_map_state(map_id)
    current_accessible = map_state.get("accessible_maps", [])
    
    if is_accessible and target_map_id not in current_accessible:
        current_accessible.append(target_map_id)
    elif not is_accessible and target_map_id in current_accessible:
        current_accessible.remove(target_map_id)
    
    # 更新map_state中的可访问性
    map_state["accessible_maps"] = current_accessible
    save_map_state(map_id, map_state)
    
    print(f"地图{map_id}到地图{target_map_id}的可访问性已更新为: {is_accessible}")

def initialize_map_accessibility_from_db(map_id: int = None):
    """从数据库初始化指定地图的可访问性到map_state，如果不指定则初始化所有地图"""
    try:
        from databaseManager import db_manager
        
        if map_id is not None:
            # 只初始化指定地图
            maps_data = db_manager.execute_query("SELECT id, accessible_locations FROM maps WHERE id = ?", (map_id,))
        else:
            # 初始化所有地图
            maps_data = db_manager.execute_query("SELECT id, accessible_locations FROM maps ORDER BY id")
        
        for map_data in maps_data:
            current_map_id = map_data['id']
            accessible_locations = map_data.get('accessible_locations')
            
            if accessible_locations:
                try:
                    accessible_list = json.loads(accessible_locations)
                    # 获取现有map_state或创建新的
                    map_state = get_map_state(current_map_id)
                    map_state["accessible_maps"] = accessible_list
                    save_map_state(current_map_id, map_state)
                    print(f"地图{current_map_id}的可访问性已初始化到map_state: {accessible_list}")
                except json.JSONDecodeError:
                    print(f"地图{current_map_id}的可访问性数据格式错误: {accessible_locations}")
            else:
                map_state = get_map_state(current_map_id)
                map_state["accessible_maps"] = []
                save_map_state(current_map_id, map_state)
                print(f"地图{current_map_id}的可访问性已初始化为空列表")
                
    except Exception as e:
        print(f"初始化地图可访问性失败: {e}")

# --- 3. 角色静态数据 (Character Sheet) ---
def save_character_sheet(character_id: str, sheet_data: Dict[str, Any]):
    redis_client = get_redis_client()
    if not redis_client: return
    key = f"{SHEET_KEY_PREFIX}{character_id}"
    redis_client.setex(key, 86400, json.dumps(sheet_data, ensure_ascii=False))

def get_character_sheet(character_id: str) -> Dict[str, Any]:
    redis_client = get_redis_client()
    if not redis_client: return {}
    key = f"{SHEET_KEY_PREFIX}{character_id}"
    data = redis_client.get(key)
    return json.loads(data) if data else {}

# --- 4. 角色动态数据 (Session State) ---
def save_session_state(character_id: str, session_data: Dict[str, Any]):
    redis_client = get_redis_client()
    if not redis_client: return
    key = f"{SESSION_KEY_PREFIX}{character_id}"
    redis_client.setex(key, 86400, json.dumps(session_data, ensure_ascii=False))

def get_session_state(character_id: str) -> Dict[str, Any]:
    redis_client = get_redis_client()
    if not redis_client: return {}
    key = f"{SESSION_KEY_PREFIX}{character_id}"
    data = redis_client.get(key)
    return json.loads(data) if data else {}

# --- 5. 对话历史 & 已完成事件 ---
def get_conversation_history(character_id: str) -> List[Dict[str, str]]:
    redis_client = get_redis_client()
    if not redis_client: return []
    key = f"{CONVERSATION_KEY_PREFIX}{character_id}"
    data = redis_client.get(key)
    return json.loads(data) if data else []

def save_conversation_history(character_id: str, history: List[Dict[str, str]]):
    redis_client = get_redis_client()
    if not redis_client: return
    key = f"{CONVERSATION_KEY_PREFIX}{character_id}"
    redis_client.setex(key, 86400, json.dumps(history, ensure_ascii=False))

def get_completed_event_ids(character_id: str) -> List[int]:
    redis_client = get_redis_client()
    if not redis_client: return []
    key = f"{COMPLETED_EVENTS_KEY_PREFIX}{character_id}"
    data = redis_client.get(key)
    return json.loads(data) if data else []

def save_completed_event_ids(character_id: str, event_ids: List[int]):
    redis_client = get_redis_client()
    if not redis_client: return
    key = f"{COMPLETED_EVENTS_KEY_PREFIX}{character_id}"
    redis_client.setex(key, 86400, json.dumps(event_ids))

# --- 6. 核心逻辑函数 ---
def get_pending_check_event_id(character_id: str) -> Optional[int]:
    session = get_session_state(character_id)
    pending_id = session.get("pending_check_event_id")
    return int(pending_id) if pending_id is not None else None

def save_pending_check_event_id(character_id: str, event_id: Optional[int]):
    session = get_session_state(character_id)
    if event_id:
        session["pending_check_event_id"] = event_id
    elif "pending_check_event_id" in session:
        del session["pending_check_event_id"]
    save_session_state(character_id, session)

def apply_state_changes(player_character_id: str, state_changes: List[Dict[str, Any]]):
    redis_client = get_redis_client()
    if not redis_client or not state_changes: return

    mapping = { 10: "sanity", 11: "mp", 13: "hp" }
    
    for change in state_changes:
        target_key = change.get("target")
        if not target_key: continue

        target_id = player_character_id if target_key == "player" else target_key
        
        session = get_session_state(target_id)

        if not session:
            print(f"为目标 {target_id} 初始化 session_state...")
            from databaseManager import db_manager
            sheet = get_character_sheet(target_id)
            if not sheet:
                sheet = db_manager.get_character_data(target_id)
                if not sheet:
                    print(f"错误: 无法为 target '{target_id}' 加载角色数据，跳过状态变更。")
                    continue
                save_character_sheet(target_id, sheet)

            derived_attrs = sheet.get('derived_attributes', {})
            session = {
                "hp": derived_attrs.get("hit_points", 10),
                "sanity": derived_attrs.get("sanity", 50),
                "mp": derived_attrs.get("magic_points", 10),
                "current_map_id": sheet.get('info', {}).get('current_location_id', 1),
                "current_vehicle_id": sheet.get('info', {}).get('current_vehicle_id', None),
            }

        if "attribute_id" in change and "change" in change:
            attr_id = change["attribute_id"]
            if attr_id in mapping:
                field_name = mapping[attr_id]
                current_value = int(session.get(field_name, 0))
                new_value = current_value + int(change["change"])
                session[field_name] = new_value
                print(f"角色 {target_id} 的 {field_name} 从 {current_value} 变为 {new_value}")

        if "set_state" in change:
            for key, value in change["set_state"].items():
                # 确保 None 值能正确保存
                if value is None:
                    session[key] = None
                    print(f"角色 {target_id} 的状态 {key} 已设置为 None")
                else:
                    session[key] = value
                    print(f"角色 {target_id} 的状态 {key} 已设置为 {value}")
        
        save_session_state(target_id, session)

def apply_map_state_changes(map_state_changes: List[Dict[str, Any]]):
    """应用地图状态变更（包括地图可访问性）"""
    if not map_state_changes: return
    
    for change in map_state_changes:
        if "modify_location_accessible" in change:
            # 处理地图可访问性变更
            modification = change["modify_location_accessible"]
            if isinstance(modification, list):
                for mod in modification:
                    if isinstance(mod, dict) and "from_map" in mod and "to_map" in mod and "action" in mod:
                        from_map = mod["from_map"]
                        to_map = mod["to_map"]
                        action = mod["action"]  # "add" 或 "remove"
                        
                        is_accessible = (action == "add")
                        update_map_accessibility(from_map, to_map, is_accessible)
                        print(f"事件影响：地图{from_map}到地图{to_map}的可访问性已{'增加' if is_accessible else '移除'}")
            else:
                print(f"modify_location_accessible 格式错误，应为列表: {modification}")
        
        # 可以添加更多地图状态变更的处理逻辑
        print(f"应用地图状态变更: {change}")
