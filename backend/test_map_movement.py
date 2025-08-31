# test_map_movement.py
# 测试地图移动功能

import asyncio
from map_movement import map_movement_manager
from character_state import _current_character_id
from redis_manager import get_session_state, get_map_state

async def test_map_movement():
    print("=== 测试地图移动功能 ===")
    
    # 设置测试角色ID
    test_character_id = "a1c67702144ef6fc1c513683da6fe9f4ae969ee4cb33081f78dd2cf62cf7e0fd"
    
    print(f"1. 测试角色当前状态:")
    print("-" * 50)
    
    # 获取当前地图信息
    current_map_info = map_movement_manager.get_map_info(1)
    print(f"当前地图1: {current_map_info}")
    
    # 获取可访问地图
    accessible_maps = map_movement_manager.get_accessible_maps(1)
    print(f"地图1可访问的地图: {accessible_maps}")
    
    print(f"\n2. 测试移动到地图2 (加油站咖啡馆):")
    print("-" * 50)
    
    # 测试移动
    success = map_movement_manager.move_character_to_map(test_character_id, 2)
    if success:
        print("✅ 移动成功！")
        
        # 获取移动后的状态
        session_state = get_session_state(test_character_id)
        new_map_id = session_state.get('current_map_id', 1)
        print(f"新地图ID: {new_map_id}")
        
        # 获取新地图状态
        new_map_state = get_map_state(new_map_id)
        print(f"新地图状态: {new_map_state}")
        
        # 获取移动描述
        movement_desc = map_movement_manager.get_movement_description(test_character_id, 2)
        print(f"移动描述: {movement_desc}")
        
    else:
        print("❌ 移动失败！")
    
    print(f"\n3. 测试移动到地图3 (阿卡姆市区):")
    print("-" * 50)
    
    # 测试移动到地图3
    success = map_movement_manager.move_character_to_map(test_character_id, 3)
    if success:
        print("✅ 移动成功！")
        
        session_state = get_session_state(test_character_id)
        new_map_id = session_state.get('current_map_id', 1)
        print(f"新地图ID: {new_map_id}")
        
        new_map_state = get_map_state(new_map_id)
        print(f"新地图状态: {new_map_state}")
        
        movement_desc = map_movement_manager.get_movement_description(test_character_id, 3)
        print(f"移动描述: {movement_desc}")
        
    else:
        print("❌ 移动失败！")
    
    print(f"\n4. 测试无效移动:")
    print("-" * 50)
    
    # 测试移动到不存在的地图
    success = map_movement_manager.move_character_to_map(test_character_id, 999)
    if not success:
        print("✅ 正确阻止了无效移动！")
    else:
        print("❌ 应该阻止无效移动！")
    
    print(f"\n5. 测试完成！")

if __name__ == "__main__":
    asyncio.run(test_map_movement())
