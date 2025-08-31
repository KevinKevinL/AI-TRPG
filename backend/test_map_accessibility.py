# test_map_accessibility.py
# 测试地图可访问性管理功能

from redis_manager import (
    initialize_map_accessibility_from_db,
    get_map_accessibility,
    update_map_accessibility,
    apply_map_state_changes
)

def test_map_accessibility():
    print("=== 测试地图可访问性管理功能 ===")
    
    print("1. 从数据库初始化地图可访问性:")
    print("-" * 50)
    initialize_map_accessibility_from_db()
    
    print(f"\n2. 检查各地图的可访问性:")
    print("-" * 50)
    for map_id in range(1, 4):
        accessible = get_map_accessibility(map_id)
        print(f"地图{map_id}可访问: {accessible}")
    
    print(f"\n3. 测试事件11：大树挡住去路，地图3不可访问:")
    print("-" * 50)
    map_state_changes = [{"modify_location_accessible": [{"from_map": 1, "to_map": 3, "action": "remove"}]}]
    apply_map_state_changes(map_state_changes)
    
    print(f"\n4. 检查更新后的可访问性:")
    print("-" * 50)
    for map_id in range(1, 4):
        accessible = get_map_accessibility(map_id)
        print(f"地图{map_id}可访问: {accessible}")
    
    print(f"\n5. 测试恢复地图3的可访问性:")
    print("-" * 50)
    map_state_changes = [{"modify_location_accessible": [{"from_map": 1, "to_map": 3, "action": "add"}]}]
    apply_map_state_changes(map_state_changes)
    
    print(f"\n6. 最终检查:")
    print("-" * 50)
    for map_id in range(1, 4):
        accessible = get_map_accessibility(map_id)
        print(f"地图{map_id}可访问: {accessible}")
    
    print(f"\n7. 测试完成！")

if __name__ == "__main__":
    test_map_accessibility()
