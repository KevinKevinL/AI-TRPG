# test_simple_accessibility.py
# 简单测试地图可访问性功能

from redis_manager import (
    initialize_map_accessibility_from_db,
    get_map_accessibility,
    apply_map_state_changes
)

def test_simple():
    print("=== 简单测试地图可访问性 ===")
    
    print("1. 初始化:")
    initialize_map_accessibility_from_db()
    
    print("\n2. 检查初始状态:")
    for map_id in range(1, 4):
        accessible = get_map_accessibility(map_id)
        print(f"地图{map_id}: {accessible}")
    
    print("\n3. 测试移除地图3:")
    changes = [{"modify_location_accessible": [{"from_map": 1, "to_map": 3, "action": "remove"}]}]
    apply_map_state_changes(changes)
    
    print("\n4. 检查移除后:")
    for map_id in range(1, 4):
        accessible = get_map_accessibility(map_id)
        print(f"地图{map_id}: {accessible}")
    
    print("\n5. 测试恢复地图3:")
    changes = [{"modify_location_accessible": [{"from_map": 1, "to_map": 3, "action": "add"}]}]
    apply_map_state_changes(changes)
    
    print("\n6. 检查恢复后:")
    for map_id in range(1, 4):
        accessible = get_map_accessibility(map_id)
        print(f"地图{map_id}: {accessible}")

if __name__ == "__main__":
    test_simple()
