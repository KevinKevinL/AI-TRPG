# character_state.py
"""
角色状态管理模块
用于在不同模块间共享角色信息
"""

# 全局变量存储当前角色ID
_current_character_id = None

def set_current_character_id(character_id: str):
    """
    设置当前角色ID
    """
    global _current_character_id
    _current_character_id = character_id
    print(f"角色状态已更新: {character_id}")

def get_current_character_id() -> str:
    """
    获取当前角色ID
    """
    return _current_character_id

def clear_current_character_id():
    """
    清除当前角色ID
    """
    global _current_character_id
    _current_character_id = None
    print("角色状态已清除")

def is_character_loaded() -> bool:
    """
    检查是否有角色已加载
    """
    return _current_character_id is not None
