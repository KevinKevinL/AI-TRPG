# databaseManager.py

import sqlite3
import os
from typing import Dict, Any, Optional, List

class DatabaseManager:
    def __init__(self, db_path: str = None):
        """
        初始化数据库管理器
        参数: db_path - 数据库文件路径，如果为None则使用../database.db
        """
        if db_path is None:
            # 数据库文件在backend的上层目录
            import os
            current_dir = os.path.dirname(os.path.abspath(__file__))
            self.db_path = os.path.join(current_dir, "..", "database.db")
        else:
            self.db_path = db_path
        
        print(f"数据库路径: {os.path.abspath(self.db_path)}")
        self.ensure_database_exists()
    
    def ensure_database_exists(self):
        """确保数据库文件存在"""
        if not os.path.exists(self.db_path):
            print(f"警告：数据库文件 {self.db_path} 不存在")
    
    def get_connection(self):
        """获取数据库连接"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # 使结果可以通过列名访问
            return conn
        except Exception as e:
            print(f"数据库连接失败: {e}")
            return None
    
    def execute_query(self, query: str, params: tuple = ()) -> Optional[List[Dict]]:
        """
        执行SQL查询
        参数: 
            query - SQL查询语句
            params - 查询参数
        返回: 查询结果列表或None
        """
        conn = self.get_connection()
        if not conn:
            return None
        
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            
            if query.strip().upper().startswith('SELECT'):
                # SELECT查询，返回结果
                results = cursor.fetchall()
                return [dict(row) for row in results]
            else:
                # 非SELECT查询，提交更改
                conn.commit()
                return None
                
        except Exception as e:
            print(f"查询执行失败: {e}")
            print(f"SQL: {query}")
            print(f"参数: {params}")
            return None
        finally:
            conn.close()
    
    #角色相关
    def get_character_data(self, character_id: str) -> Optional[Dict[str, Any]]:
        """
        获取角色的完整数据
        参数: character_id - 角色ID
        返回: 包含角色所有数据的字典
        """
        if not character_id:
            print("错误：角色ID为空")
            return None
        
        print(f"正在获取角色 {character_id} 的数据...")
        
        # 获取基础角色信息
        character_info = self.get_character_info(character_id)
        if not character_info:
            print(f"错误：无法找到角色 {character_id}")
            return None
        
        # 获取属性数据
        attributes = self.get_character_attributes(character_id)
        
        # 获取派生属性数据
        derived_attributes = self.get_character_derived_attributes(character_id)
        
        # 获取技能数据
        skills = self.get_character_skills(character_id)
        
        # 组合所有数据
        character_data = {
            'id': character_id,
            'info': character_info,
            'attributes': attributes,
            'derived_attributes': derived_attributes,
            'skills': skills
        }
        
        print(f"角色数据获取完成: {character_data}")
        return character_data
    
    def get_character_info(self, character_id: str) -> Optional[Dict[str, Any]]:
        """获取角色基础信息"""
        query = """
        SELECT * FROM Characters 
        WHERE id = ?
        """
        result = self.execute_query(query, (character_id,))
        return result[0] if result else None
    
    def get_character_attributes(self, character_id: str) -> Dict[str, int]:
        """获取角色属性数据"""
        query = """
        SELECT strength, constitution, size, dexterity, appearance, 
               intelligence, power, education, luck
        FROM attributes 
        WHERE character_id = ?
        """
        result = self.execute_query(query, (character_id,))
        
        if result and len(result) > 0:
            return dict(result[0])
        else:
            print(f"警告：角色 {character_id} 的属性数据不存在")
            return {}
    
    def get_character_derived_attributes(self, character_id: str) -> Dict[str, int]:
        """获取角色派生属性数据"""
        query = """
        SELECT sanity, magicPoints, interestPoints, hitPoints, 
               moveRate, damageBonus, build, professionalPoints
        FROM derivedattributes
        WHERE character_id = ?
        """
        result = self.execute_query(query, (character_id,))
        
        if result and len(result) > 0:
            return dict(result[0])
        else:
            print(f"警告：角色 {character_id} 的派生属性数据不存在")
            return {}
    
    def get_character_skills(self, character_id: str) -> Dict[str, int]:
        """获取角色技能数据"""
        query = """
        SELECT Fighting, Firearms, Dodge, Mechanics, Drive, Stealth,
               Investigate, Sleight_of_Hand, Electronics, History, Science,
               Medicine, Occult, Library_Use, Art, Persuade, Psychology
        FROM skills
        WHERE character_id = ?
        """
        result = self.execute_query(query, (character_id,))
        
        if result and len(result) > 0:
            return dict(result[0])
        else:
            print(f"警告：角色 {character_id} 的技能数据不存在")
            return {}
    
    def get_attribute_by_name(self, character_data: Dict[str, Any], attribute_name: str) -> Optional[int]:
        """
        根据属性名获取属性值
        参数:
            character_data - 角色数据
            attribute_name - 属性名
        返回: 属性值或None
        """
        
        # 在属性中查找
        attributes = character_data.get('attributes', {})
        for key, value in attributes.items():
            if key.lower() == attribute_name:
                return value
        
        # 在派生属性中查找
        derived_attributes = character_data.get('derived_attributes', {})
        for key, value in derived_attributes.items():
            if key.lower() == attribute_name:
                return value
        
        # 在技能中查找
        skills = character_data.get('skills', {})
        for key, value in skills.items():
            if key.lower() == attribute_name:
                return value
        
        print(f"警告：未找到属性 '{attribute_name}'")
        return None
    
    def get_character_list(self) -> List[Dict[str, Any]]:
        """获取所有角色列表"""
        query = """
        SELECT id, name, profession, age, gender
        FROM characters
        ORDER BY name
        """
        return self.execute_query(query) or []

# 创建全局数据库管理器实例
db_manager = DatabaseManager()

# 便捷函数，用于其他模块调用
def get_character_data(character_id: str) -> Optional[Dict[str, Any]]:
    """获取角色数据的便捷函数"""
    return db_manager.get_character_data(character_id)

def get_attribute_by_name(character_data: Dict[str, Any], attribute_name: str) -> Optional[int]:
    """根据属性名获取属性值的便捷函数"""
    return db_manager.get_attribute_by_name(character_data, attribute_name)

def get_character_list() -> List[Dict[str, Any]]:
    """获取角色列表的便捷函数"""
    return db_manager.get_character_list()
