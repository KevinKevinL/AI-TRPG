# player_action_parser.py

import os
import json
import asyncio
import websockets
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
import random

# 导入您项目中的模块
from databaseManager import db_manager, get_character_data, get_attribute_by_name
from character_state import get_current_character_id, is_character_loaded

# 加载环境变量
load_dotenv()

# --- WebSocket 管理 (从skillCheck.py保留) ---
# 注意：为了在异步环境中正确广播，您可能需要一个全局的事件循环引用
# 或者将广播逻辑改为异步函数
websocket_connections = set()
_loop = None

def set_event_loop(loop):
    """设置全局事件循环"""
    global _loop
    _loop = loop

def add_websocket_connection(websocket):
    """添加WebSocket连接到管理器"""
    websocket_connections.add(websocket)

def remove_websocket_connection(websocket):
    """移除WebSocket连接"""
    websocket_connections.discard(websocket)

def broadcast_dice_result_sync(dice_data):
    """同步广播骰子结果到所有连接的客户端"""
    if websocket_connections and _loop:
        message = json.dumps({'type': 'skill_check_result', **dice_data})
        for ws in list(websocket_connections):
            try:
                # 确保在正确的事件循环中发送
                asyncio.run_coroutine_threadsafe(ws.send_text(message), _loop)
            except Exception as e:
                print(f"发送骰子结果失败: {e}")
                websocket_connections.discard(ws)

# --- 核心功能: 意图解析 (全新) ---

async def parse_player_action(player_input: str, available_npcs: list = [], available_objects: list = []) -> dict:
    """
    将玩家的自然语言输入解析为结构化的意图JSON。
    """
    print("--- 玩家意图解析器开始 ---")
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

    npc_list_str = ", ".join([f"'{n.get('name', '未知NPC')}' (id: {n.get('id', 'unknown')})" for n in available_npcs])
    object_list_str = ", ".join([f"'{o.get('object_name', '未知物品')}' (id: {o.get('object_id', 'unknown')})" for o in available_objects])

    system_prompt = f"""
    你是一个COC跑团的指令解析器。根据玩家输入，分析其核心意图，并生成结构化的JSON响应。

    # 1. 可用指令 (intent) 列表:
    - inspect: 观察、检查、搜寻 (关键词: 看, 检查, 调查, 搜)
    - talk: 对话 (关键词: 问, 说, 聊, 告诉)
    - take: 拿取 (关键词: 拿, 捡, 获取)
    - use: 使用 (关键词: 用, 使用)
    - use_skill: 明确意图使用某项能力 (关键词: 尝试, 试图, 我要检定[技能名])
    - move: 移动 (关键词: 走, 前往, 回到, 去)
    - leave_woman: (特殊指令) 抛下艾米利亚离开
    - help_woman: (特殊指令) 帮助艾米利亚
    - take_amelia_in_car: (特殊指令) 让艾米利亚上车 (关键词: 上车, 载她, 带她走, 一起走)

    # 2. 可用目标 (target) 列表:
    - NPC: [{npc_list_str}]
    - 物品: [{object_list_str}]
    - 地点: 回阿卡姆的路(地图3), 加油站咖啡馆(地图2), 离开阿卡姆的郊外公路(地图1)

    # 3. 可用技能列表：
    - 核心属性: strength(力量), constitution(体质), size(体型), dexterity(敏捷), appearance(外貌), intelligence(智力), power(意志), education(教育), luck(幸运)
    - 衍生属性: sanity(理智), magic_points(魔法值), interest_points(兴趣点), hit_points(生命值), move_rate(移动率), damage_bonus(伤害加值), build(体格), professional_points(职业点)
    - 战斗技能: fighting(格斗), firearms(枪械), dodge(闪避)
    - 技术技能: mechanics(机械维修), drive(驾驶), stealth(潜行), investigate(调查), sleight_of_hand(妙手), electronics(电子学)
    - 知识技能: history(历史), science(科学), medicine(医学), occult(神秘学), library_use(图书馆使用), art(艺术)
    - 社交技能: persuade(说服), psychology(心理学)
    - 财富等级: credit_rating(富有程度)

    # 4. 解析规则:
    - 'intent' 必须是上述列表之一。
    - 'target' 必须是可用的NPC ID、物品名称、技能名称或特殊目标名称之一。
    - 'topic' 仅在 'intent' 为 'talk' 时提取谈话主题。
    - 当玩家输入较明确是特殊指令时，忽略所有其他指令，直接返回特殊指令。

    # 4. 示例:
    玩家输入: "艾米利亚，你爷爷是做什么的？"
    JSON: {{"intent": "talk", "target": "amelia_weber", "topic": "祖父"}}
    
    玩家输入: "我开车走了，不管她了。"
    JSON: {{"intent": "leave_woman"}}

    玩家输入："下车帮助她"
    JSON: {{"intent": "help_woman"}}
    
    玩家输入："上车避雨吧"
    JSON: {{"intent": "take_amelia_in_car"}}
    
    玩家输入："我要尝试回忆附近有什么地方"
    JSON: {{"intent": "use_skill", "skill_check_request": ["intelligence"]}}
    
    玩家输入："我想仔细观察这个挂坠"
    JSON: {{"intent": "use_skill", "skill_check_request": ["occult"]}}
    
    玩家输入："我要回阿卡姆"
    JSON: {{"intent": "move", "target": "阿卡姆", "target_location_id": 3}}
    
    严格只返回JSON对象。
    """
    
    messages = [SystemMessage(content=system_prompt), HumanMessage(content=player_input)]
    response = await llm.ainvoke(messages)
    
    try:
        parsed_action = json.loads(response.content)
        print(f"玩家意图解析结果: {parsed_action}")
        return parsed_action
    except json.JSONDecodeError:
        print(f"JSON解析错误: {response.content}")
        return {"intent": "unknown", "raw_text": player_input}

# --- 辅助功能: 技能检定 (从skillCheck.py保留并改造) ---

def get_key_by_skill_id(skill_id):
    """根据 skill_id 获取对应的属性或技能名"""
    # 这个映射表对于系统至关重要
    all_keys = {
        1: 'strength', 2: 'constitution', 3: 'size', 4: 'dexterity', 5: 'appearance',
        6: 'intelligence', 7: 'power', 8: 'education', 9: 'luck', 
        10: 'sanity', 11: 'magic_points', 12: 'interest_points', 13: 'hit_points',
        14: 'move_rate', 15: 'damage_bonus', 16: 'build', 17: 'professional_points',
        18: 'fighting', 19: 'firearms', 20: 'dodge',
        21: 'mechanics', 22: 'drive', 23: 'stealth', 24: 'investigate', 25: 'sleight_of_hand',
        26: 'electronics', 27: 'history', 28: 'science', 29: 'medicine', 30: 'occult',
        31: 'library_use', 32: 'art', 33: 'persuade', 34: 'psychology'
    }
    return all_keys.get(skill_id)

def _roll_d100():
    """私有函数：生成 1d100 掷骰结果"""
    return random.randint(1, 100)

def _get_skill_check_threshold(skill_value: int, hard_level: int) -> int:
    """私有函数：获取技能检定阈值"""
    if hard_level == 1: return skill_value
    if hard_level == 2: return skill_value // 2
    if hard_level == 3: return skill_value // 5
    return skill_value

def _check_skill_logic(character_data: dict, skill_name: str, hard_level: int) -> dict:
    """私有函数：执行技能检定的核心逻辑"""
    skill_value = get_attribute_by_name(character_data, skill_name)
    if skill_value is None:
        print(f"警告：未找到技能或属性 '{skill_name}'，使用默认值0")
        skill_value = 0
    
    threshold = _get_skill_check_threshold(skill_value, hard_level)
    dice_roll = _roll_d100()
    is_success = dice_roll <= threshold
    
    print(f"检定 {skill_name}: 技能值={skill_value}, 难度={hard_level}, 掷骰: {dice_roll} / 阈值: {threshold}")
    
    return {
        'skill_name': skill_name,
        'skill_value': skill_value,
        'hard_level': hard_level,
        'threshold': threshold,
        'dice_roll': dice_roll,
        'success': is_success
    }

def check_skill_directly(character_id: str, skill_id: int, difficulty: int = 1):
    """
    根据技能ID和难度，直接为指定角色执行一次检定。
    这是我们新架构中执行检定的标准接口。
    """
    try:
        skill_name = get_key_by_skill_id(skill_id)
        if not skill_name:
            raise ValueError(f"未知的技能ID: {skill_id}")

        character_data = get_character_data(character_id)
        if not character_data:
            raise ValueError(f"无法获取角色 {character_id} 的数据")
        
        result = _check_skill_logic(character_data, skill_name, difficulty)
        
        # 广播骰子结果到前端
        try:
            broadcast_dice_result_sync(result)
        except Exception as e:
            print(f"推送骰子结果失败: {e}")
        
        return result
        
    except Exception as e:
        print(f"直接技能检定失败: {e}")
        return {"success": False, "error": str(e)}

def generate_result_description(skill_check_result: dict) -> str:
    """
    (保留) 生成检定结果的描述文本，在Narrative Synthesizer中可能用到
    """
    if not skill_check_result: return "检定结果为空"
    
    difficulty_names = {1: "普通", 2: "困难", 3: "极难"}
    difficulty_name = difficulty_names.get(skill_check_result.get('hard_level', 1), "未知")
    status = "✅ 成功" if skill_check_result.get('success') else "❌ 失败"
    
    return (
        f"【{difficulty_name}难度检定结果】\n"
        f"{skill_check_result.get('skill_name')}: "
        f"{skill_check_result.get('dice_roll')}/{skill_check_result.get('threshold')} {status}"
    )

def get_skill_value_from_sheet(character_sheet: dict, key: str) -> int:
    """从角色sheet中读取任意属性/技能值，不存在时返回0。"""
    if not character_sheet or not isinstance(character_sheet, dict):
        return 0
    for section in ("attributes", "derived_attributes", "skills"):
        section_dict = character_sheet.get(section, {})
        if isinstance(section_dict, dict) and key in section_dict:
            try:
                return int(section_dict[key])
            except (ValueError, TypeError):
                # 若不是纯数值，尽量返回0以避免崩溃
                return 0
    return 0

