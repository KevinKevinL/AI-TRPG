# databaseManager.py

import sqlite3
import os
from typing import Dict, Any, Optional, List
import json

class DatabaseManager:
    def __init__(self, db_path: str = None):
        if db_path is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            self.db_path = os.path.join(current_dir, "..", "database.db")
        else:
            self.db_path = db_path
        print(f"数据库路径: {os.path.abspath(self.db_path)}")
        self.ensure_database_exists()

    def ensure_database_exists(self):
        if not os.path.exists(self.db_path):
            print(f"警告：数据库文件 {self.db_path} 不存在")

    def get_connection(self):
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            return conn
        except Exception as e:
            print(f"数据库连接失败: {e}")
            return None

    def execute_query(self, query: str, params: tuple = ()) -> Optional[List[Dict]]:
        conn = self.get_connection()
        if not conn:
            return None
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            if query.strip().upper().startswith('SELECT'):
                results = cursor.fetchall()
                return [dict(row) for row in results]
            else:
                conn.commit()
                return None
        except Exception as e:
            print(f"查询执行失败: {e}")
            print(f"SQL: {query}")
            print(f"参数: {params}")
            return None
        finally:
            conn.close()

    def get_initial_world_state(self) -> Dict[str, Any]:
        query = "SELECT state_key, state_value FROM world_state"
        results = self.execute_query(query)
        world_state = {}
        if results:
            for row in results:
                try:
                    world_state[row['state_key']] = json.loads(row['state_value'])
                except (json.JSONDecodeError, TypeError):
                    world_state[row['state_key']] = row['state_value']
        print(f"从数据库加载了初始世界状态: {world_state}")
        return world_state

    # --- 新增：获取地图实体 ---
    def get_npcs_on_map(self, map_id: int) -> List[Dict[str, Any]]:
        """获取指定地图上的所有NPC基础信息"""
        query = "SELECT id, name FROM characters WHERE if_npc = 1 AND current_location_id = ?"
        return self.execute_query(query, (map_id,)) or []

    def get_objects_on_map(self, map_id: int) -> List[Dict[str, Any]]:
        """获取指定地图上的所有可交互物品信息"""
        query = "SELECT object_id, object_name, current_state FROM interactable_objects WHERE map_id = ?"
        results = self.execute_query(query, (map_id,))
        # 解析 current_state 字符串为 JSON
        if results:
            for item in results:
                try:
                    item['current_state'] = json.loads(item['current_state']) if item['current_state'] else {}
                except (json.JSONDecodeError, TypeError):
                    item['current_state'] = {}
        return results or []
    
    # --- 角色相关 (原有函数保持不变) ---
    def get_character_data(self, character_id: str) -> Optional[Dict[str, Any]]:
        if not character_id: return None
        character_info = self.get_character_info(character_id)
        if not character_info: return None
        return {
            'info': character_info,
            'attributes': self.get_character_attributes(character_id),
            'derived_attributes': self.get_character_derived_attributes(character_id),
            'skills': self.get_character_skills(character_id),
            'backgrounds': self.get_character_backgrounds(character_id)
        }
    
    def get_character_info(self, character_id: str) -> Optional[Dict[str, Any]]:
        query = "SELECT * FROM characters WHERE id = ?"
        result = self.execute_query(query, (character_id,))
        return result[0] if result else None
    
    def get_character_attributes(self, character_id: str) -> Dict[str, int]:
        query = "SELECT * FROM attributes WHERE character_id = ?"
        result = self.execute_query(query, (character_id,))
        return result[0] if result else {}
    
    def get_character_derived_attributes(self, character_id: str) -> Dict[str, int]:
        query = "SELECT * FROM derived_attributes WHERE character_id = ?"
        result = self.execute_query(query, (character_id,))
        return result[0] if result else {}
    
    def get_character_skills(self, character_id: str) -> Dict[str, int]:
        query = "SELECT * FROM skills WHERE character_id = ?"
        result = self.execute_query(query, (character_id,))
        return result[0] if result else {}

    def get_character_backgrounds(self, character_id: str) -> Dict[str, str]:
        query = "SELECT * FROM backgrounds WHERE character_id = ?"
        result = self.execute_query(query, (character_id,))
        return result[0] if result else {}
    
    def get_attribute_by_name(self, character_sheet: Dict[str, Any], attribute_name: str) -> Optional[int]:
        for section in ['attributes', 'derived_attributes', 'skills']:
            if attribute_name in character_sheet.get(section, {}):
                return character_sheet[section][attribute_name]
        print(f"警告：在角色卡中未找到属性 '{attribute_name}'")
        return None
    
    def update_npc_state(self, character_id: str, new_status: Optional[str] = None, new_goal: Optional[str] = None):
        updates, params = [], []
        if new_status:
            updates.append("status = ?")
            params.append(new_status)
        if new_goal:
            updates.append("current_goal = ?")
            params.append(new_goal)
        if not updates: return
        params.append(character_id)
        query = f"UPDATE characters SET {', '.join(updates)} WHERE id = ?"
        self.execute_query(query, tuple(params))
        print(f"数据库中NPC {character_id} 的状态已更新。")

    # 注意：NPC记忆现在使用ChromaDB存储，这些方法已废弃
    # 请使用 memory_manager.py 中的方法

db_manager = DatabaseManager()

# --- 模块级别导出函数 ---
def get_character_data(character_id: str) -> Optional[Dict[str, Any]]:
    """获取角色数据的便捷函数"""
    return db_manager.get_character_data(character_id)

def get_attribute_by_name(character_sheet: Dict[str, Any], attribute_name: str) -> Optional[int]:
    """根据属性名获取属性值的便捷函数"""
    return db_manager.get_attribute_by_name(character_sheet, attribute_name)

def get_character_list() -> List[Dict[str, Any]]:
    """获取角色列表的便捷函数"""
    return db_manager.get_character_list()
