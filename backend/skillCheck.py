# skillCheck.py

import os
import json
import asyncio
import websockets
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from character_state import get_current_character_id, is_character_loaded
from databaseManager import get_character_data, get_attribute_by_name
import random

# 加载环境变量
load_dotenv()

# 全局WebSocket连接管理器
websocket_connections = set()

def add_websocket_connection(websocket):
    """添加WebSocket连接到管理器"""
    websocket_connections.add(websocket)

def remove_websocket_connection(websocket):
    """移除WebSocket连接"""
    websocket_connections.discard(websocket)

def broadcast_dice_result_sync(dice_data):
    """同步广播骰子结果到所有连接的客户端"""
    if websocket_connections:
        message = json.dumps({
            'type': 'skill_check_result',
            **dice_data
        })
        
        # 同步发送到所有连接
        for ws in list(websocket_connections):
            try:
                if hasattr(ws, 'send_text'):
                    # FastAPI WebSocket
                    asyncio.create_task(ws.send_text(message))
                elif hasattr(ws, 'send'):
                    # 原生websockets
                    asyncio.create_task(ws.send(message))
            except Exception as e:
                print(f"发送骰子结果失败: {e}")
                # 移除无效连接
                websocket_connections.discard(ws)

def skill_check(player_input: str):
    """
    主要的技能检定函数
    参数: player_input - 玩家的输入文本
    返回: 技能检定结果的字符串描述
    """
    print("---Skill Check 开始---")
    
    # 检查是否有角色已加载
    if not is_character_loaded():
        return "错误：没有角色已加载，请先进入游戏页面"
    
    # 获取当前角色ID
    current_character_id = get_current_character_id()
    print(f"当前角色ID: {current_character_id}")
    
    # 首先调用API进行技能意图识别
    try:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("请在 .env 文件中设置 OPENAI_API_KEY")

        llm = ChatOpenAI(api_key=api_key, model="gpt-4o-mini", temperature=0)
        
        # 使用提供的prompt进行技能意图识别
        system_message = """
        你是一个桌面RPG游戏主持人(KP)。根据玩家的输入和上下文，分析情况并生成以下格式的JSON响应（严格JSON格式）：
        如果玩家输入中包含他想要利用某个属性或技能来通过检定，请优先考虑玩家想要利用的属性或技能。但是请注意，如果玩家想要利用的属性或技能和想做的行动不符，请不要使用该属性或技能，而是你来决定相符的属性或技能。
                 {
           "testRequired": [<list of attributes or skills to test>], // 例如：["strength", "library_use"]。如果不需要检定，返回空数组 []
           "hardlevel": <1 | 2 | 3 | null>, // 难度：1=普通，2=困难，3=极难。如果不需要检定，返回null
         }

        可用的属性和技能有：

            属性：
            - strength: 身体力量
            - constitution: 身体耐力和韧性
            - size: 身体大小和质量
            - dexterity: 敏捷性和协调性
            - appearance: 外表吸引力
            - intelligence: 推理和记忆能力
            - power: 意志力和精神韧性
            - education: 正式知识和训练水平
            - luck: 幸运结果

            衍生属性：
             - sanity: 精神稳定性和对心理创伤的抵抗力
             - magic_points: 魔法或超自然行为的容量
             - interest_points: 分配给爱好的点数
             - hit_points: 身体健康
             - move_rate: 移动速度
             - damage_bonus: 基于身体强壮程度的额外伤害
             - build: 整体身体强壮程度
             - professional_points: 专业技能点数

            技能：
             - fighting: 近战战斗熟练度
             - firearms: 远程战斗熟练度
             - dodge: 躲避攻击的能力
             - mechanics: 修理和操作机械设备能力
             - drive: 操作车辆能力
             - stealth: 潜行能力
             - investigate: 发现线索和分析能力
             - sleight_of_hand: 手部灵巧程度
             - electronics: 电子设备操作能力
             - history: 历史和考古知识
             - science: 基础科学理解
             - medicine: 医学知识和手术能力
             - occult: 神秘学主题知识
             - library_use: 检索信息能力
             - art: 艺术创作和欣赏
             - persuade: 社交谈判技能
             - psychology: 心理学知识

        重要：如果玩家的输入不需要任何技能检定或属性测试，请返回：
        {
          "testRequired": [],
          "hardlevel": null
        }

        只返回该JSON对象，不要添加额外文本。"""
        
        messages = [SystemMessage(content=system_message), HumanMessage(content=player_input)]
        response = llm.invoke(messages)
        
        # 解析响应
        try:
            skill_check_data = json.loads(response.content)
            print(f"技能检定数据: {skill_check_data}")
            
            # 执行技能检定
            if skill_check_data.get('testRequired') and skill_check_data.get('hardlevel'):
                result = perform_check(skill_check_data, current_character_id)
                return result
            else:
                return "当前情况不需要进行技能检定或属性测试"
                
        except json.JSONDecodeError as e:
            print(f"JSON解析错误: {e}")
            return f"技能检定解析失败: {e}"
            
    except Exception as e:
        print(f"技能检定过程中发生错误: {e}")
        return f"技能检定失败: {e}"

def perform_check(skill_check_data, character_id: str):
    """
    执行技能检定的函数
    参数: 
        skill_check_data - 包含检定信息的字典
        character_id - 当前角色ID
    返回: 检定结果的字符串描述
    """
    print(f"为角色 {character_id} 执行技能检定")
    
    # 获取检定参数
    test_required = skill_check_data.get('testRequired', [])
    hard_level = skill_check_data.get('hardlevel', 1)
    
    # 添加调试信息
    print(f"原始检定数据: {skill_check_data}")
    print(f"需要检定: {test_required}, 难度: {hard_level} (类型: {type(hard_level)})")
    
    # 处理空值情况
    if not test_required or test_required == []:
        return "当前情况不需要进行技能检定或属性测试"
    
    if hard_level is None:
        return "当前情况不需要进行技能检定或属性测试"
    
    # 获取角色数据
    character_data = get_character_data(character_id)
    if not character_data:
        return f"错误：无法获取角色 {character_id} 的数据"
    
    # 添加角色数据调试信息
    print(f"角色数据: {character_data}")
    
    # 执行技能检定
    skill_check_results = {}
    dice_results = []  # 存储骰子结果用于前端显示
    
    for skill_name in test_required:
        result = check_skill(character_data, skill_name, hard_level)
        skill_check_results[skill_name] = result
        
        # 准备骰子结果数据
        dice_data = {
            'skill_name': skill_name,
            'dice_roll': result['dice_roll'],
            'threshold': result['threshold'],
            'success': result['success'],
            'hard_level': hard_level
        }
        dice_results.append(dice_data)
        
        # 推送骰子结果到前端
        try:
            broadcast_dice_result_sync(dice_data)
        except Exception as e:
            print(f"推送骰子结果失败: {e}")
    
    # 生成检定结果描述
    result_description = generate_result_description(skill_check_results, hard_level)
    
    # 将骰子结果添加到返回数据中
    result_data = {
        'description': result_description,
        'dice_results': dice_results,
        'skill_check_results': skill_check_results
    }
    
    return result_data

def roll_d100():
    """生成 1d100 掷骰结果"""
    return random.randint(1, 100)

def get_skill_check_threshold(skill_value: int, hard_level: int) -> int:
    """获取技能检定阈值"""
    if hard_level == 1:
        return skill_value  # 普通难度（全值）
    elif hard_level == 2:
        return skill_value // 2  # 困难难度（半值）
    elif hard_level == 3:
        return skill_value // 5  # 极难难度（五分之一）
    else:
        return 0

def check_skill(character_data: dict, skill_name: str, hard_level: int) -> dict:
    """进行技能检定"""
    # 确保难度值是整数
    try:
        hard_level = int(hard_level)
    except (ValueError, TypeError):
        hard_level = 1  # 默认普通难度
        print(f"警告：难度值 '{hard_level}' 无法转换为整数，使用默认值1")
    
    # 使用数据库管理器获取技能值
    skill_value = get_attribute_by_name(character_data, skill_name)
    
    if skill_value is None:
        skill_value = 0
        print(f"警告：未找到技能或属性 '{skill_name}'，使用默认值0")
    
    # 添加调试信息
    print(f"检定 {skill_name}: 技能值={skill_value}, 难度={hard_level}")
    
    threshold = get_skill_check_threshold(skill_value, hard_level)
    dice_roll = roll_d100()
    
    # 判断成功或失败
    is_success = dice_roll <= threshold
    
    print(f"掷骰: {dice_roll} / 阈值: {threshold} (技能: {skill_name}, 难度: {hard_level})")
    
    return {
        'skill_name': skill_name,
        'skill_value': skill_value,
        'hard_level': hard_level,
        'threshold': threshold,
        'dice_roll': dice_roll,
        'success': is_success,
        'result': '成功' if is_success else '失败'
    }

def generate_result_description(skill_check_results: dict, hard_level: int) -> str:
    """生成检定结果的描述文本"""
    if not skill_check_results:
        return "检定结果为空"
    
    # 难度描述
    difficulty_names = {1: "普通", 2: "困难", 3: "极难"}
    difficulty_name = difficulty_names.get(hard_level, "未知")
    
    # 统计成功和失败
    successes = sum(1 for result in skill_check_results.values() if result['success'])
    total = len(skill_check_results)
    
    # 生成详细结果
    result_lines = [f"【{difficulty_name}难度检定结果】"]
    
    for skill_name, result in skill_check_results.items():
        status = "✅ 成功" if result['success'] else "❌ 失败"
        result_lines.append(
            f"{skill_name}: {result['dice_roll']}/{result['threshold']} {status}"
        )
    
    # 添加总结
    if successes == total:
        result_lines.append(f"\n🎉 全部检定成功！({successes}/{total})")
    elif successes == 0:
        result_lines.append(f"\n💥 全部检定失败！({successes}/{total})")
    else:
        result_lines.append(f"\n📊 检定完成：{successes}/{total} 成功")
    
    return "\n".join(result_lines)

# 新增：获取当前角色信息的辅助函数
def get_character_info():
    """
    获取当前角色信息
    返回: 角色ID或None
    """
    if is_character_loaded():
        return {
            "character_id": get_current_character_id(),
            "status": "loaded"
        }
    else:
        return {
            "character_id": None,
            "status": "not_loaded"
        }

def get_key_by_testRequired(test_required):
    """根据 testRequired 获取对应的属性或技能名"""
    all_keys = {
        1: 'strength',
        2: 'constitution',
        3: 'size',
        4: 'dexterity',
        5: 'appearance',
        6: 'intelligence',
        7: 'power',
        8: 'education',
        9: 'luck',
        10: 'sanity',
        11: 'magic_points',
        12: 'interest_points',
        13: 'hit_points',
        14: 'move_rate',
        15: 'damage_bonus',
        16: 'build',
        17: 'professional_points',
        18: 'fighting',
        19: 'firearms',
        20: 'dodge',
        21: 'mechanics',
        22: 'drive',
        23: 'stealth',
        24: 'investigate',
        25: 'sleight_of_hand',
        26: 'electronics',
        27: 'history',
        28: 'science',
        29: 'medicine',
        30: 'occult',
        31: 'library_use',
        32: 'art',
        33: 'persuade',
        34: 'psychology',
    }
    return all_keys[test_required] if test_required in all_keys else None

def get_attribute_field_mapping():
    """
    获取属性ID到Redis字段的映射
    
    Returns:
        Dict: 属性ID到(数据类型, 字段名)的映射
    """
    mapping = {}
    
    # 基础属性 (1-9)
    for attr_id in range(1, 10):
        key_name = get_key_by_testRequired(attr_id)
        if key_name:
            mapping[attr_id] = ("attributes", key_name)
    
    # 派生属性 (10-17)
    for attr_id in range(10, 18):
        key_name = get_key_by_testRequired(attr_id)
        if key_name:
            mapping[attr_id] = ("status", key_name)
    
    # 技能 (18-34)
    for attr_id in range(18, 35):
        key_name = get_key_by_testRequired(attr_id)
        if key_name:
            mapping[attr_id] = ("skills", key_name)
    
    return mapping

def check_skill_directly(skill_name: str, hard_level: int = 1):
    """直接进行技能检定，不需要LLM识别"""
    try:
        # 获取当前角色ID
        current_character_id = get_current_character_id()
        if not current_character_id:
            raise ValueError("没有角色已加载")
        
        # 获取角色数据
        character_data = get_character_data(current_character_id)
        if not character_data:
            raise ValueError(f"无法获取角色 {current_character_id} 的数据")
        
        # 进行技能检定
        result = check_skill(character_data, skill_name, hard_level)
        
        # 推送骰子结果到前端
        try:
            dice_data = {
                'skill_name': skill_name,
                'dice_roll': result['dice_roll'],
                'threshold': result['threshold'],
                'success': result['success'],
                'hard_level': hard_level
            }
            broadcast_dice_result_sync(dice_data)
        except Exception as e:
            print(f"推送骰子结果失败: {e}")
        
        return result
        
    except Exception as e:
        print(f"直接技能检定失败: {e}")
        # 返回模拟结果
        return {
            'skill_name': skill_name,
            'skill_value': 0,
            'hard_level': hard_level,
            'threshold': 0,
            'dice_roll': 0,
            'success': True,
            'result': '成功'
        }
   