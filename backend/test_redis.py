#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试Redis连接和对话历史功能
"""

import redis
import json

def test_redis_connection():
    """测试Redis连接"""
    try:
        # 连接到Redis
        r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
        
        # 测试连接
        r.ping()
        print("✅ Redis连接成功！")
        
        # 测试基本操作
        test_key = "test:connection"
        test_value = "Hello Redis!"
        
        # 设置值
        r.set(test_key, test_value)
        print(f"✅ 设置值成功: {test_key} = {test_value}")
        
        # 获取值
        retrieved_value = r.get(test_key)
        print(f"✅ 获取值成功: {test_key} = {retrieved_value}")
        
        # 清理测试数据
        r.delete(test_key)
        print(f"✅ 清理测试数据成功")
        
        return True
        
    except Exception as e:
        print(f"❌ Redis连接失败: {e}")
        return False

def test_conversation_history():
    """测试对话历史功能"""
    try:
        r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
        
        # 测试对话历史存储
        character_id = "test_character_123"
        conversation_key = f"conversation_history:{character_id}"
        
        # 模拟对话历史
        test_history = [
            {"user_input": "你好", "kp_output": "你好，冒险者！"},
            {"user_input": "今天天气怎么样？", "kp_output": "天空阴沉沉的，似乎要下雨了。"}
        ]
        
        # 保存对话历史
        r.setex(conversation_key, 3600, json.dumps(test_history, ensure_ascii=False))
        print(f"✅ 保存对话历史成功: {conversation_key}")
        
        # 获取对话历史
        retrieved_history = r.get(conversation_key)
        if retrieved_history:
            parsed_history = json.loads(retrieved_history)
            print(f"✅ 获取对话历史成功: {parsed_history}")
        else:
            print("❌ 获取对话历史失败")
            return False
        
        # 清理测试数据
        r.delete(conversation_key)
        print(f"✅ 清理测试数据成功")
        
        return True
        
    except Exception as e:
        print(f"❌ 对话历史测试失败: {e}")
        return False

if __name__ == "__main__":
    print("🧪 开始测试Redis功能...")
    print("=" * 50)
    
    # 测试Redis连接
    if test_redis_connection():
        print("\n" + "=" * 50)
        
        # 测试对话历史功能
        if test_conversation_history():
            print("\n🎉 所有测试通过！Redis功能正常。")
        else:
            print("\n❌ 对话历史测试失败。")
    else:
        print("\n❌ Redis连接测试失败。")
