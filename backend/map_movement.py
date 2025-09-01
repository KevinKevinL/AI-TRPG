# map_movement.py
# 地图移动管理模块

import json
from typing import Dict, Any, Optional
from databaseManager import db_manager
from redis_manager import (
    get_session_state, save_session_state,
    get_map_state, save_map_state,
    get_character_sheet, save_character_sheet,
    get_map_accessibility, update_map_accessibility
)

class MapMovementManager:
    def __init__(self):
        self.db_manager = db_manager
    
    def get_accessible_maps(self, current_map_id: int) -> list:
        """获取当前地图可访问的其他地图（优先使用Redis中的动态状态）"""
        try:
            # 优先从Redis获取动态可访问性
            redis_accessible = get_map_accessibility(current_map_id)
            if redis_accessible:
                print(f"从Redis获取地图{current_map_id}的可访问性: {redis_accessible}")
                return redis_accessible
            
            # 如果Redis中没有，从数据库获取并初始化
            result = self.db_manager.execute_query(
                "SELECT accessible_locations FROM maps WHERE id = ?",
                (current_map_id,)
            )
            if result and result[0].get('accessible_locations'):
                accessible = json.loads(result[0]['accessible_locations'])
                # 保存到Redis
                from redis_manager import save_map_accessibility
                save_map_accessibility(current_map_id, accessible)
                print(f"从数据库初始化地图{current_map_id}的可访问性: {accessible}")
                return accessible
            return []
        except Exception as e:
            print(f"获取可访问地图失败: {e}")
            return []
    
    def get_map_info(self, map_id: int) -> Optional[Dict[str, Any]]:
        """获取地图信息"""
        try:
            result = self.db_manager.execute_query(
                "SELECT * FROM maps WHERE id = ?",
                (map_id,)
            )
            if result:
                return result[0]
            return None
        except Exception as e:
            print(f"获取地图信息失败: {e}")
            return None
    
    def can_move_to_map(self, character_id: str, target_map_id: int) -> bool:
        """检查角色是否可以移动到目标地图"""
        try:
            # 获取角色当前位置
            character_sheet = get_character_sheet(character_id)
            current_location_id = character_sheet.get('info', {}).get('current_location_id', 1)
            
            # 检查目标地图是否在可访问列表中（使用Redis中的动态状态）
            accessible_maps = self.get_accessible_maps(current_location_id)
            can_move = target_map_id in accessible_maps
            
            print(f"角色 {character_id} 从地图{current_location_id}移动到地图{target_map_id}: {'✅ 允许' if can_move else '❌ 禁止'}")
            print(f"地图{current_location_id}的可访问地图: {accessible_maps}")
            
            return can_move
            
        except Exception as e:
            print(f"检查移动权限失败: {e}")
            return False
    
    def move_character_to_map(self, character_id: str, target_map_id: int) -> bool:
        """将角色移动到目标地图"""
        try:
            # 检查移动权限
            if not self.can_move_to_map(character_id, target_map_id):
                print(f"角色 {character_id} 无法移动到地图 {target_map_id}")
                return False
            
            # 获取目标地图信息
            target_map = self.get_map_info(target_map_id)
            if not target_map:
                print(f"目标地图 {target_map_id} 不存在")
                return False
            
            # 更新数据库中的位置
            update_query = "UPDATE characters SET current_location_id = ? WHERE id = ?"
            self.db_manager.execute_query(update_query, (target_map_id, character_id))
            
            # 更新Redis中的session_state
            session_state = get_session_state(character_id)
            session_state['current_map_id'] = target_map_id
            save_session_state(character_id, session_state)
            
            # 加载新地图的状态到Redis
            new_map_state = self._load_map_state_to_redis(target_map_id)
            if new_map_state:
                save_map_state(target_map_id, new_map_state)
            
            print(f"角色 {character_id} 成功移动到地图 {target_map_id}: {target_map.get('map_name', '未知地图')}")
            return True
            
        except Exception as e:
            print(f"移动角色失败: {e}")
            return False
    
    def _load_map_state_to_redis(self, map_id: int) -> Dict[str, Any]:
        """将地图状态加载到Redis"""
        try:
            # 获取地图上的NPC
            npcs = self.db_manager.execute_query(
                "SELECT id FROM characters WHERE if_npc = 1 AND current_location_id = ?",
                (map_id,)
            )
            npc_ids = [npc['id'] for npc in npcs]
            
            # 为新地图的NPC初始化记忆系统和session_state
            self._initialize_npc_memories_for_map(map_id, npc_ids)
            self._initialize_npc_session_states_for_map(map_id, npc_ids)
            
            # 获取地图上的可交互对象
            objects = self.db_manager.execute_query(
                "SELECT object_id, object_name, current_state FROM interactable_objects WHERE map_id = ?",
                (map_id,)
            )
            objects_state = {}
            for obj in objects:
                obj_id = str(obj['object_id'])
                # 保持与character.py中相同的数据结构
                objects_state[obj_id] = json.loads(obj['current_state']) if obj['current_state'] else {}
            
            # 获取地图的可访问性信息
            accessible_maps = self.get_accessible_maps(map_id)
            
            map_state = {
                "npcs": npc_ids,
                "objects": objects_state,
                "accessible_maps": accessible_maps  # 新增：可访问性信息
            }
            
            return map_state
            
        except Exception as e:
            print(f"加载地图状态到Redis失败: {e}")
            return {"npcs": [], "objects": {}, "accessible_maps": []}
    
    def get_movement_description(self, character_id: str, target_map_id: int) -> str:
        """获取移动描述文本"""
        try:
            current_sheet = get_character_sheet(character_id)
            current_location_id = current_sheet.get('info', {}).get('current_location_id', 1)
            
            current_map = self.get_map_info(current_location_id)
            target_map = self.get_map_info(target_map_id)
            
            if current_map and target_map:
                return f"你从{current_map['map_name']}移动到了{target_map['map_name']}。{target_map['map_info']}"
            
            return f"你移动到了地图{target_map_id}"
            
        except Exception as e:
            print(f"获取移动描述失败: {e}")
            return "你移动到了新的地点"
    
    def _initialize_npc_memories_for_map(self, map_id: int, npc_ids: list):
        """为新地图的NPC初始化记忆系统"""
        try:
            from memory_manager import memory_manager
            
            def get_map_name(map_id):
                """获取地图名称"""
                map_names = {
                    1: '阿卡姆郊外公路',
                    2: '加油站咖啡馆',
                    3: '前往阿卡姆的道路'
                }
                return map_names.get(map_id, f'地图{map_id}')
            
            for npc_id in npc_ids:
                try:
                    # 检查NPC是否已有记忆
                    existing_memories = memory_manager.get_npc_memories(npc_id, limit=1)
                    if not existing_memories:
                        # 获取NPC信息
                        npc_sheet = self.db_manager.get_character_data(npc_id)
                        if npc_sheet:
                            npc_name = npc_sheet.get('info', {}).get('name', npc_id)
                            map_name = get_map_name(map_id)
                            
                            # 为NPC创建初始记忆
                            initial_memory = f"我是{npc_name}，正在{map_name}。"
                            
                            memory_manager.add_npc_memory(
                                character_id=npc_id,
                                memory_text=initial_memory,
                                context={
                                    "initialization": True,
                                    "map_id": map_id,
                                    "npc_name": npc_name,
                                    "map_name": map_name
                                }
                            )
                            print(f"为新地图{map_id}的NPC {npc_id} 创建了初始记忆")
                        else:
                            print(f"警告：无法获取NPC {npc_id} 的完整数据")
                    else:
                        print(f"NPC {npc_id} 已有记忆，跳过初始化")
                except Exception as e:
                    print(f"初始化NPC {npc_id} 记忆时出错: {e}")
                    
        except Exception as e:
            print(f"初始化地图{map_id}的NPC记忆时出错: {e}")

    def _initialize_npc_session_states_for_map(self, map_id: int, npc_ids: list):
        """为新地图的NPC初始化session_state"""
        try:
            for npc_id in npc_ids:
                try:
                    # 检查NPC是否已有session_state
                    existing_session = get_session_state(npc_id)
                    if not existing_session:
                        # 获取NPC的完整数据
                        npc_sheet = self.db_manager.get_character_data(npc_id)
                        if npc_sheet:
                            # 确保NPC的完整数据保存到Redis
                            save_character_sheet(npc_id, npc_sheet)
                            
                            npc_derived = npc_sheet.get('derived_attributes', {})
                            npc_session = {
                                "hp": npc_derived.get("hit_points", 10),
                                "sanity": npc_derived.get("sanity", 50),
                                "mp": npc_derived.get("magic_points", 10),
                                "current_map_id": npc_sheet.get('info', {}).get('current_location_id', map_id),
                                "current_vehicle_id": npc_sheet.get('info', {}).get('current_vehicle_id', None),
                            }
                            save_session_state(npc_id, npc_session)
                            print(f"为新地图{map_id}的NPC {npc_id} 创建了session_state")
                        else:
                            print(f"警告：无法获取NPC {npc_id} 的完整数据")
                    else:
                        print(f"NPC {npc_id} 已有session_state，跳过创建")
                except Exception as e:
                    print(f"初始化NPC {npc_id} session_state时出错: {e}")
                    
        except Exception as e:
            print(f"初始化地图{map_id}的NPC session_state时出错: {e}")


# 创建全局实例
map_movement_manager = MapMovementManager()
