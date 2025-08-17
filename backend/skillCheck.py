# skillCheck.py

import os
import json
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from character_state import get_current_character_id, is_character_loaded
from databaseManager import get_character_data, get_attribute_by_name
import random

# 加载环境变量
load_dotenv()

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
        system_message = """You are a tabletop RPG game master (KP). Based on the user's input and the context, analyze the situation and generate a JSON response in the following format (in strict JSON):

{
  "testRequired": [<list of attributes or skills to test>],
  "hardlevel": <1 | 2 | 3>, // Difficulty: 1=Easy, 2=Hard, 3=Very Hard
}

The available attributes and skills are:

    Attributes:
    - strength (STR): Physical strength.
    - constitution (CON): Physical endurance and resilience.
    - size (SIZ): Physical size and mass.
    - dexterity (DEX): Agility and coordination.
    - appearance (APP): Physical attractiveness.
    - intelligence (INT): Reasoning and memory capacity.
    - power (POW): Willpower and mental fortitude.
    - education (EDU): Level of formal knowledge and training.
    - luck (Luck): Fortuitous outcomes.

    Derived Attributes:
    - sanity (SAN): Mental stability and resistance to psychological trauma.
    - magicPoints (MP): Capacity for magical or supernatural actions.
    - interestPoints (Interest): Points allocated for hobbies.
    - hitPoints (HP): Physical health.
    - moveRate (MOV): Speed.
    - damageBonus (DB): Additional damage based on physical build.
    - build (Build): Overall physical build.
    - professionalPoints (Profession Points): Points for professional skills.

    Skills:
    - Fighting: Melee combat proficiency. Base: 25.
    - Firearms: Ranged combat proficiency. Base: 20.
    - Dodge: Ability to evade attacks. Base: 20.
    - Mechanics: Repair and operate devices. Base: 10.
    - Drive: Operate vehicles. Base: 20.
    - Stealth: Move silently. Base: 20.
    - Investigate: Spot clues and analyze. Base: 25.
    - Sleight of Hand: Manual dexterity tasks. Base: 10.
    - Electronics: Repair electronic equipment. Base: 10.
    - History: Knowledge of history and archaeology. Base: 10.
    - Science: Understanding basic sciences. Base: 10.
    - Medicine: Medical knowledge and surgery. Base: 5.
    - Occult: Knowledge of occult topics. Base: 5.
    - Library Use: Locate information in archives. Base: 20.
    - Art: Artistic creation and appreciation. Base: 5.
    - Persuade: Social negotiation skills. Base: 15.
    - Psychology: Analyze human behavior. Base: 10.

Respond only with that JSON object, and no extra text."""
        
        messages = [SystemMessage(content=system_message), HumanMessage(content=player_input)]
        response = llm.invoke(messages)
        
        # 解析JSON响应
        try:
            skill_check_data = json.loads(response.content)
            print(f"技能检定识别结果: {skill_check_data}")
            
            # 调用技能检定执行函数，传入角色ID
            result = perform_check(skill_check_data, current_character_id)
            return result
            
        except json.JSONDecodeError as e:
            print(f"JSON解析失败: {e}")
            return "技能检定识别失败，无法解析响应"
            
    except Exception as e:
        print(f"技能检定运行出错: {e}")
        return f"技能检定处理失败: {str(e)}"

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
    
    if not test_required:
        return "没有需要检定的技能或属性"
    
    # 获取角色数据
    character_data = get_character_data(character_id)
    if not character_data:
        return f"错误：无法获取角色 {character_id} 的数据"
    
    # 添加角色数据调试信息
    print(f"角色数据: {character_data}")
    
    # 执行技能检定
    skill_check_results = {}
    for skill_name in test_required:
        result = check_skill(character_data, skill_name, hard_level)
        skill_check_results[skill_name] = result
    
    # 生成检定结果描述
    result_description = generate_result_description(skill_check_results, hard_level)
    
    return result_description

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
