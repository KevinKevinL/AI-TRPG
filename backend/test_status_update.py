"""
测试角色状态更新功能的脚本
"""

import asyncio
import sys
import os

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from redis_manager import (
    get_redis_client, 
    update_character_attribute_by_id,
    get_character_status_from_redis
)
from character_state import get_current_character_id, set_current_character_id

async def test_status_update():
    """测试角色状态更新功能"""
    
    print("=== 测试角色状态更新功能 ===")
    
    # 设置测试角色ID
    test_character_id = "test_character_123"
    set_current_character_id(test_character_id)
    
    print(f"测试角色ID: {test_character_id}")
    
    # 1. 测试获取当前状态
    print("\n1. 获取当前角色状态...")
    current_status = get_character_status_from_redis(test_character_id)
    print(f"当前状态: {current_status}")
    
    # 2. 测试生命值更新
    print("\n2. 测试生命值更新...")
    health_change = -2
    update_success = update_character_attribute_by_id(
        test_character_id, 
        [(13, health_change)]  # 13 = hit_points
    )
    
    if update_success:
        print(f"生命值更新成功: 变化量 {health_change:+d}")
        updated_status = get_character_status_from_redis(test_character_id)
        print(f"更新后状态: {updated_status}")
    else:
        print("生命值更新失败")
    
    # 3. 测试理智值更新
    print("\n3. 测试理智值更新...")
    sanity_change = -5
    update_success = update_character_attribute_by_id(
        test_character_id, 
        [(10, sanity_change)]  # 10 = Sanity
    )
    
    if update_success:
        print(f"理智值更新成功: 变化量 {sanity_change:+d}")
        updated_status = get_character_status_from_redis(test_character_id)
        print(f"更新后状态: {updated_status}")
    else:
        print("理智值更新失败")
    
    # 4. 测试同时更新两个值
    print("\n4. 测试同时更新生命值和理智值...")
    health_change = -1
    sanity_change = -3
    update_success = update_character_attribute_by_id(
        test_character_id, 
        [(13, health_change), (10, sanity_change)]  # 生命值和理智值同时更新
    )
    
    if update_success:
        print(f"状态更新成功: 生命值变化 {health_change:+d}, 理智值变化 {sanity_change:+d}")
        final_status = get_character_status_from_redis(test_character_id)
        print(f"最终状态: {final_status}")
    else:
        print("状态更新失败")
    
    # 5. 测试边界情况（生命值不能低于0）
    print("\n5. 测试边界情况...")
    large_health_loss = -20
    update_success = update_character_attribute_by_id(
        test_character_id, 
        [(13, large_health_loss)]  # 生命值大额损失
    )
    
    if update_success:
        print(f"大额生命值损失处理成功: 尝试减少 {large_health_loss:+d}")
        final_status = get_character_status_from_redis(test_character_id)
        print(f"最终状态: {final_status}")
        print(f"生命值被限制在最小值: {final_status.get('hit_points', 0)}")
    else:
        print("大额生命值损失处理失败")
    
    # 6. 测试新的通用属性更新功能
    print("\n6. 测试通用属性更新功能...")
    
    # 测试同时更新多个属性
    attribute_changes = [
        (10, -2),  # 理智值 -2
        (13, -1),  # 生命值 -1
        (18, +1),  # 格斗技能 +1
        (1, -1)    # 力量 -1
    ]
    
    update_success = update_character_attribute_by_id(
        test_character_id, 
        attribute_changes
    )
    
    if update_success:
        print("多属性同时更新成功")
        final_status = get_character_status_from_redis(test_character_id)
        print(f"最终状态: {final_status}")
    else:
        print("多属性同时更新失败")
    
    print("\n=== 测试完成 ===")

if __name__ == "__main__":
    # 运行测试
    asyncio.run(test_status_update())
