from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import TypedDict, List, Dict, Any, Optional
from langgraph.graph import StateGraph, END
import random
import os
import json
import ast
import time
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
import skillCheck
import random_event
from databaseManager import db_manager
from character_state import get_current_character_id
from redis_manager import get_redis_client, get_character_data_from_redis

# 导入新的 RAG 引擎模块
from rag_engine import rag_engine

# 加载环境变量
load_dotenv()

# 对话历史存储的键前缀
CONVERSATION_KEY_PREFIX = "conversation_history:"

# 关键事件存储的键前缀
KEY_EVENTS_KEY_PREFIX = "key_events:"

# 新增的 Redis 关键事件操作函数
def get_completed_events(character_id: str) -> List[str]:
    """从Redis获取已完成的关键事件列表"""
    try:
        redis_client = get_redis_client()
        if not redis_client:
            return []
        key = f"{KEY_EVENTS_KEY_PREFIX}{character_id}:events"
        data = redis_client.get(key)
        if data:
            return json.loads(data)
        return []
    except Exception as e:
        print(f"获取已完成事件列表失败: {e}")
        return []

def save_completed_events(character_id: str, events: List[str]):
    """保存已完成的关键事件列表到Redis"""
    try:
        redis_client = get_redis_client()
        if not redis_client:
            return
        key = f"{KEY_EVENTS_KEY_PREFIX}{character_id}:events"
        redis_client.setex(key, 86400, json.dumps(events, ensure_ascii=False))
    except Exception as e:
        print(f"保存已完成事件列表失败: {e}")

def get_completed_event_ids(character_id: str) -> List[int]:
    """从Redis获取已完成的事件ID列表"""
    try:
        redis_client = get_redis_client()
        if not redis_client:
            return []
        key = f"{KEY_EVENTS_KEY_PREFIX}{character_id}:ids"
        data = redis_client.get(key)
        if data:
            return json.loads(data)
        return []
    except Exception as e:
        print(f"获取已完成事件ID列表失败: {e}")
        return []

def save_completed_event_ids(character_id: str, event_ids: List[int]):
    """保存已完成的事件ID列表到Redis"""
    try:
        redis_client = get_redis_client()
        if not redis_client:
            return
        key = f"{KEY_EVENTS_KEY_PREFIX}{character_id}:ids"
        redis_client.setex(key, 86400, json.dumps(event_ids, ensure_ascii=False))
    except Exception as e:
        print(f"保存已完成事件ID列表失败: {e}")
        
def get_conversation_history(character_id: str) -> List[Dict[str, str]]:
    """从Redis获取对话历史"""
    try:
        redis_client = get_redis_client()
        if not redis_client:
            print("Redis客户端不可用，返回初始对话记录")
            return get_initial_conversation()
            
        key = f"{CONVERSATION_KEY_PREFIX}{character_id}"
        data = redis_client.get(key)
        if data:
            return json.loads(data)
        
        print("未找到对话历史，返回初始对话记录")
        return get_initial_conversation()
        
    except Exception as e:
        print(f"获取对话历史失败: {e}")
        return get_initial_conversation()

def get_initial_conversation() -> List[Dict[str, str]]:
    """返回初始的对话记录"""
    return [
        {
            "user_input": "进入跑团",
            "kp_output": "夜幕如同黑色的裹尸布，将世界包裹得严严实实。你从阿卡姆启程，正驱车前往外地处理一桩棘手的委托。然而，一场突如其来的风暴彻底打乱了你的计划。豆大的雨点疯狂地砸向车顶，闪电撕裂漆黑的夜空，照亮了车窗上扭曲的雨痕。你的车只能像一只爬行的甲虫，在泥泞的道路上缓慢挪动，努力用前灯的光穿透雨幕，避免迷失方向......"
        }
    ]

def save_conversation_history(character_id: str, history: List[Dict[str, str]]):
    """保存对话历史到Redis"""
    try:
        redis_client = get_redis_client()
        if not redis_client:
            print("Redis客户端不可用，无法保存对话历史")
            return
            
        key = f"{CONVERSATION_KEY_PREFIX}{character_id}"
        # 设置过期时间为24小时
        redis_client.setex(key, 86400, json.dumps(history, ensure_ascii=False))
    except Exception as e:
        print(f"保存对话历史失败: {e}")

# --- 1. 定义 LangGraph 状态和 Pydantic 模型 ---
class AgentState(TypedDict):
    """代表图的当前状态的类。"""
    # 基础输入输出
    player_input: str
    happening_event_id: int
    happening_event_result: int
    happening_event_info: str
    final_output: str
    conversation_history: List[Dict[str, str]]  # 对话历史
    
    # 角色数据信息 - 用于function calling
    character_info: Dict[str, Any]  # 角色基本信息
    character_attributes: Dict[str, int]  # 角色属性值
    character_skills: Dict[str, int]  # 角色技能值
    character_derived_attributes: Dict[str, int]  # 派生属性值
    character_background: str  # 角色背景
    character_profession: str  # 角色职业
    character_sanity: int  # 理智值
    character_health: int  # 生命值
    character_magic: int  # 魔法值
    
    # 游戏状态信息
    current_map_id: str  # 当前地图ID
    skill_check_result_info: Dict[str, Any] # 技能检定结果
    completed_happened_events: List[str] # 已完成的剧情事件
    completed_happened_event_ids: List[int] # 已完成的剧情事件id
    
    # 前端状态管理
    character_state_updated: bool  # 标记角色状态是否已更新，用于前端刷新
    
    # 环境信息
    nearby_objects: List[str]  # 附近物品
    npc_presence: List[str]  # 在场NPCid列表


# --- 2. 定义 Agent 节点函数 ---
def router_agent(state: AgentState):
    """处理初始状态，不负责路由"""
    print("---Router Agent 开始---")
    print(f"当前状态: happening_event_id={state.get('happening_event_id', 'NOT_FOUND')}")
    print(f"状态类型: {type(state.get('happening_event_id', 'NOT_FOUND'))}")
    
    # 只处理状态，不返回路由信息
    print("Router Agent 处理完成，状态已准备就绪")
    return state

async def main_event_agent(state: AgentState):
    """在无主线事件正在进行时，决定是否触发一个新主线事件，并生成剧情"""
    print("---Main Event Agent 开始---")
    print(f"收到玩家输入: {state.get('player_input', 'NOT_FOUND')}")
    print(f"当前地图ID: {state.get('current_map_id', 'NOT_FOUND')}")
    print(f"已完成事件ID列表: {state.get('completed_happened_event_ids', [])}")
    print(f"已完成事件列表: {state.get('completed_happened_events', [])}")
    print(f"对话历史长度: {len(state.get('conversation_history', []))}")
    
    player_input = state["player_input"]
    chat_history = state.get("conversation_history", [])
    
    # 调用_event模块的LLM决策逻辑，决定本轮是否触发事件
    event_decision_raw = await random_event.get_random_event_result(
        player_input,
        state.get("current_map_id", "1"),
        state.get("completed_happened_event_ids", []),
        state.get("completed_happened_events", []),
        chat_history,
    )
    
    print(f"LLM原始响应: {event_decision_raw}")
    
    # 解析LLM返回的JSON字符串
    try:
        if isinstance(event_decision_raw, str):
            event_decision = json.loads(event_decision_raw)
        else:
            event_decision = event_decision_raw
        print(f"解析后的事件决策: {event_decision}")
    except json.JSONDecodeError as e:
        print(f"JSON解析失败: {e}")
        event_decision = {"event_id": -1, "kp_narrative": "事件解析失败", "event_info": "解析失败"}

    if event_decision and event_decision.get("event_id", -1) != -1:
        # 获取事件信息
        selected_event_id = event_decision.get("event_id")
        sql_query = "SELECT event_info, test_required_id FROM events WHERE event_id = ?"
        result = db_manager.execute_query(sql_query, (selected_event_id,))
        
        event_info = result[0].get("event_info") if result else "未知事件"
        test_required_id = result[0].get("test_required_id") if result else -1
        # 兼容 None/空值：视为无检定
        if test_required_id is None:
            test_required_id = -1

        if test_required_id == -1:
            # 如果不需要检定
            # 将事件标记为已完成
            print(f"事件 {selected_event_id} 不需要检定")
            completed_events = state.get("completed_happened_events", [])
            completed_event_ids = state.get("completed_happened_event_ids", [])
            
            # 确保不重复添加
            if selected_event_id not in completed_event_ids:
                completed_event_ids.append(selected_event_id)
                completed_events.append(event_info)
                
            # 更新happened_result为1
            sql_query = "UPDATE events SET happened_result = 1 WHERE event_id = ?"
            db_manager.execute_query(sql_query, (selected_event_id,))
            print(f"事件 {selected_event_id} 的 happened_result 已更新为 1")
            
            # 处理状态修改 - 对于不需要检定的事件，只获取成功时的修改配置
            sql_query = """
                SELECT success_modify_id, success_modify_num
                FROM events 
                WHERE event_id = ?
            """
            event_config_result = db_manager.execute_query(sql_query, (selected_event_id,))
            
            if event_config_result and len(event_config_result) > 0:
                event_config = event_config_result[0]
                
                # 因为是不需要检定的事件，所以直接使用成功时的修改配置
                modify_id = event_config.get("success_modify_id")
                modify_num = event_config.get("success_modify_num", 0)
                
                # 应用状态修改 - 使用新的通用属性更新函数
                if modify_id and modify_num != 0:
                    from redis_manager import update_character_attribute_by_id
                    character_id = get_current_character_id()
                    
                    # 直接传递属性ID和变化量
                    update_success = update_character_attribute_by_id(
                        character_id, 
                        [(modify_id, modify_num)]
                    )
                    
                    if update_success:
                        print(f"角色属性已更新: 属性ID {modify_id}, 变化量 {modify_num:+d}")
                    else:
                        print("角色属性更新失败")
            
            # 直接生成最终输出
            print(f"Main Event Agent 决定触发事件: {selected_event_id}")
            
            updated_history = chat_history + [
                {"user_input": player_input, "kp_output": event_decision["final_kp_narrative"]}
            ]
            
            # 追加系统提示：事件已完成（无检定默认成功）
            system_note = {
                "kp_output": f"【系统】主线事件已完成（成功）：{event_info}",
                "event_id": selected_event_id,
                "event_result": 1
            }
            updated_history.append(system_note)
            
            return {
                "happening_event_id": -1,
                "final_output": event_decision["final_kp_narrative"],
                "conversation_history": updated_history,
                "completed_happened_events": completed_events,
                "completed_happened_event_ids": completed_event_ids,
                "character_state_updated": True  # 添加状态更新标记，让前端知道需要刷新数据
            }
        else:
            # 如果是需要检定的事件，将happening_event_id更新为事件ID，下一轮是事件轮
            print(f"Main Event Agent 决定触发需要检定的事件: {selected_event_id}")
            updated_history = chat_history + [
                {"user_input": player_input, "kp_output": event_decision["final_kp_narrative"]}
            ]
            
            return {
                "happening_event_id": selected_event_id,
                "test_required_id": test_required_id,
                "final_output": event_decision["final_kp_narrative"],
                "conversation_history": updated_history
            }
    else:
        # 无事件发生，返回空，让流程进入 No_main_event_story
        print("Main Event Agent 决定不触发事件")
        return {"happening_event_id": -1}

async def no_main_event_story_agent(state: AgentState):
    """在无主线事件时，处理技能检定和生成通用剧情"""
    print("---No Main Event Story Agent 开始---")
    print(f"开始处理技能检定，玩家输入: {state.get('player_input', 'NOT_FOUND')}")
    print(f"对话历史长度: {len(state.get('conversation_history', []))}")
    
    player_input = state["player_input"]
    chat_history = state["conversation_history"]

    # 调用skillCheck.py进行检定识别和执行
    try:
        skill_check_result = skillCheck.skill_check(player_input)
        # 移除重复的日志，因为skillCheck.skill_check内部已经有日志了
        print(f"技能检定原始返回: {skill_check_result}")

        dice_results_len = 0
        description_text = ""
        if isinstance(skill_check_result, dict):
            dice_results_len = len(skill_check_result.get('dice_results', []) or [])
            description_text = skill_check_result.get('description', '') or ''
        print(f"dice_results_len={dice_results_len}, has_description={bool(description_text)}")

        if dice_results_len > 0:
            # 有实际掷骰：带入检定结果
            system_prompt = (
                "你是一位克苏鲁跑团游戏守密人（KP）。根据玩家的输入、对话历史和检定结果，生成一段符合氛围的叙事。\n"
                "叙事规则（非常重要）：\n"
                "1) 严格保持场景连续性：延续上一轮的场景与动作，不得无过渡地切换地点或交通方式；\n"
                "2) 禁止引入对话历史中未出现的‘具体实体/地点/物件/宗教/超自然元素’；\n"
                "3) 将检定结果体现在‘当下即时反馈’上：成功=短暂优势/控制感；失败=短暂受挫/风险上升；\n"
                "4) 语言简洁，2-4句（≤120字）为宜，专注当前片刻的感官与动作，不要铺陈后续剧情；\n"
                "5) 不给出选项或命令式指引，只在结尾以轻微的开放式一句收束（非菜单式）。"
            )
            context = (
                f"玩家输入: {player_input}\n"
                f"对话历史: {chat_history}\n"
                f"技能检定结果: {description_text}\n"
            )
            llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.2)
            response = await llm.ainvoke([SystemMessage(content=system_prompt + context)])
            final_output = response.content
        else:
            # 无掷骰（包括：有描述但未掷骰、或无需检定）：统一走无检定叙事
            print("进入统一的无检定叙事实分支")
            system_prompt = (
                "你是一位克苏鲁跑团游戏守密人（KP）。根据玩家的输入和对话历史，生成一段符合氛围的叙事。\n"
                "叙事规则（非常重要）：\n"
                "1) 严格保持场景连续性：延续上一轮的场景与动作，不得无过渡地切换地点或交通方式；\n"
                "2) 禁止引入对话历史中未出现的‘具体实体/地点/物件/宗教/超自然元素’；\n"
                "3) 只描写‘当下此刻’可感知的细节（声音/光线/触感/动作），不要展开后续剧情；\n"
                "4) 语言简洁，2-4句（≤120字）为宜，仅维持气氛与张力；\n"
                "5) 不给出选项或命令式指引，只在结尾以轻微的开放式一句收束（非菜单式）。"
            )
            context = (
                f"玩家输入: {player_input}\n"
                f"对话历史: {chat_history}\n"
            )
            llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.2)
            response = await llm.ainvoke([SystemMessage(content=system_prompt + context)])
            final_output = response.content

    except Exception as e:
        print(f"技能检定处理失败: {e}")
        system_prompt = (
            "你是一位克苏鲁跑团游戏守密人（KP）。根据玩家的输入和对话历史，生成一段符合氛围的叙事。"
        )
        context = (
            f"玩家输入: {player_input}\n"
            f"对话历史: {chat_history}\n"
        )

        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)
        response = await llm.ainvoke([SystemMessage(content=system_prompt + context)])
        final_output = response.content

    updated_history = chat_history + [
        {"user_input": player_input, "kp_output": final_output}
    ]
    
    return {
        "final_output": final_output,
        "conversation_history": updated_history,
        "happening_event_id": -1,
        "completed_happened_events": state.get("completed_happened_events", []),
        "completed_happened_event_ids": state.get("completed_happened_event_ids", [])
    }
 

async def main_event_happening_agent(state: AgentState):
    """在有主线事件时，处理技能检定和状态重置"""
    print("---Main Event Happening Agent 开始---")
    
    event_id = state["happening_event_id"]
    player_input = state["player_input"]
    
    sql_query = "SELECT test_required_id,hard_level,success_result_info,fail_result_info FROM events WHERE event_id = ?"
    result = db_manager.execute_query(sql_query, (event_id,))
    test_required_id = result[0].get("test_required_id") if result and len(result) > 0 else -1
    hard_level = result[0].get("hard_level") if result and len(result) > 0 else 1
    
    skill_check_result_info = {}
    
    if test_required_id != -1:
        # 根据test_required_id直接进行技能检定，不需要LLM识别(目前是单个技能检定)
        try:
            # 获取技能名称
            skill_name = skillCheck.get_key_by_testRequired(test_required_id)
            print(f"需要检定技能: {skill_name}")
            
            if skill_name:
                # 直接进行技能检定
                skill_check_result = skillCheck.check_skill_directly(skill_name, hard_level)
                
                skill_check_result_info = {
                    "skill_name": skill_name,
                    "success": skill_check_result.get('success', False),
                    "hard_level": hard_level,
                    "threshold": skill_check_result.get('threshold', 0),
                    "dice_roll": skill_check_result.get('dice_roll', 0),
                }
                
                print(f"技能检定完成: {skill_check_result_info}")
            else:
                print(f"未知的检定ID: {test_required_id}")
                skill_check_result_info = {
                    "skill_name": "未知技能",
                    "success": False,
                    "hard_level": hard_level,
                    "threshold": 0,
                    "dice_roll": 0,
                }
                
        except Exception as e:
            print(f"技能检定失败: {e}")
            success = random.random() > 0.5
            skill_check_result_info = {
                "skill_name": "未知技能",
                "success": success,
                "hard_level": hard_level,
                "threshold": 0,
                "dice_roll": 0,
            }
    else:
        print("分支出错，正在发生的事件无检定")
        # 不需要检定
        skill_check_result_info = {
            "skill_name": "分支出错，正在发生的事件无检定",
            "success": True,
            "hard_level": hard_level,
            "threshold": 0,
            "dice_roll": 0,
        }
    
    return {
        "skill_check_result_info": skill_check_result_info
    }


async def event_happened_story_agent(state: AgentState):
    """负责根据事件结果和用户输入生成本轮给用户的文本内容"""
    print("---Event Happened Story Agent 开始---")
    
    player_input = state["player_input"]
    # 从上一个节点获取happening_event_id
    happening_event_id = state.get("happening_event_id", -1) 
    # 获取检定结果信息
    skill_check_result_info = state.get("skill_check_result_info", {})
    chat_history = state.get("conversation_history", [])
    
    # 根据事件ID和检定结果，从事件库获取成功/失败的叙述文本
    sql_query = "SELECT event_info, success_result_info, fail_result_info FROM events WHERE event_id = ?"
    event_result = db_manager.execute_query(sql_query, (happening_event_id,))
    
    event_narrative = ""
    event_info = "未知事件"
    if event_result and len(event_result) > 0:
        event_info = event_result[0]['event_info']
        if skill_check_result_info.get("success", False):
            event_narrative = event_result[0]['success_result_info']
        else:
            event_narrative = event_result[0]['fail_result_info']
    
    system_prompt = (
        "你是一位克苏鲁跑团游戏守密人（KP）。基于以下事件信息、玩家输入，以及对话历史，生成一段符合剧情的叙述。 "
        "请严格按照以下JSON格式返回：\n"
        "{\n"
        '  "kp_narrative": "你的KP叙述内容",\n'
        '  "event_summary": "事件的简要结果描述，用于记录到已完成事件列表中"\n'
        "}\n"
        "确保回复中包含事件的最终结果，并让剧情流畅地推进。"
    )
    
    context = (
        f"玩家输入: {player_input}\n"
        f"对话历史: {chat_history}\n"
        f"技能检定结果: {skill_check_result_info.get('result_description', '无')}\n"
        f"正在发生的事件信息: {event_info}\n"
        f"该事件的检定后的结果叙述: {event_narrative}\n"
    )
    
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)
    response = await llm.ainvoke([SystemMessage(content=system_prompt + context)])
    
    # 解析LLM返回的JSON
    try:
        llm_response = json.loads(response.content)
        final_output = llm_response.get("kp_narrative", "KP叙述生成失败")
        event_summary = llm_response.get("event_summary", event_info)  # 如果解析失败，使用原始事件信息
    except json.JSONDecodeError as e:
        print(f"LLM返回的JSON解析失败: {e}")
        print(f"原始返回内容: {response.content}")
        # 如果JSON解析失败，使用原始内容作为KP叙述，事件信息作为简述
        final_output = response.content
        event_summary = event_info
    
    # 更新事件状态
    success_int = 1 if skill_check_result_info.get("success", False) else 0
    sql_query = "UPDATE events SET happened_result = ? WHERE event_id = ?"
    db_manager.execute_query(sql_query, (success_int, happening_event_id))
    
    # 处理状态修改 - 根据检定结果获取对应的状态修改配置
    sql_query = """
        SELECT success_modify_id, success_modify_num, fail_modify_id, fail_modify_num 
        FROM events 
        WHERE event_id = ?
    """
    event_config_result = db_manager.execute_query(sql_query, (happening_event_id,))
    
    if event_config_result and len(event_config_result) > 0:
        event_config = event_config_result[0]
        
        if skill_check_result_info.get("success", False):
            # 检定成功，使用成功时的修改配置
            modify_id = event_config.get("success_modify_id")
            modify_num = event_config.get("success_modify_num", 0)
        else:
            # 检定失败，使用失败时的修改配置
            modify_id = event_config.get("fail_modify_id")
            modify_num = event_config.get("fail_modify_num", 0)
        
        # 应用状态修改 - 使用新的通用属性更新函数
        if modify_id and modify_num != 0:
            from redis_manager import update_character_attribute_by_id
            character_id = get_current_character_id()
            
            # 直接传递属性ID和变化量
            update_success = update_character_attribute_by_id(
                character_id, 
                [(modify_id, modify_num)]
            )
            
            if update_success:
                print(f"角色属性已更新: 属性ID {modify_id}, 变化量 {modify_num:+d}")
            else:
                print("角色属性更新失败")
    
    # 更新已完成事件列表
    completed_events = state.get('completed_happened_events', [])
    completed_event_ids = state.get('completed_happened_event_ids', [])

    if happening_event_id not in completed_event_ids:
        completed_events.append(event_summary)  # 使用新生成的事件简述
        completed_event_ids.append(happening_event_id)

    # 更新对话历史
    updated_history = chat_history + [
        {"user_input": player_input, "kp_output": final_output}
    ]

    # 追加系统提示：事件已完成（含成功/失败）
    system_note = {
        "kp_output": f"【系统】主线事件已完成（{'成功' if success_int == 1 else '失败'}）：{event_info}",
        "event_id": happening_event_id,
        "event_result": success_int
    }
    updated_history.append(system_note)

    return {
        "final_output": final_output,
        "conversation_history": updated_history,
        "completed_happened_events": completed_events,
        "completed_happened_event_ids": completed_event_ids,
        "happening_event_id": -1, # 重置事件ID
        "character_state_updated": True  # 添加状态更新标记，让前端知道需要刷新数据
    }

async def frontend_refresh_agent(state: AgentState):
    """前端状态刷新代理节点，在LangGraph结束时通知前端刷新角色状态"""
    print("---Frontend Refresh Agent 开始---")
    
    # 检查是否有角色状态更新
    character_state_updated = state.get("character_state_updated", False)
    
    if character_state_updated:
        print("检测到角色状态更新，准备通过WebSocket通知前端刷新")
        
        # 获取当前角色ID
        character_id = get_current_character_id()
        print(f"角色 {character_id} 状态已更新，前端需要刷新")
        
        # 通过WebSocket通知前端刷新角色状态
        try:
            from main import manager  # 导入WebSocket管理器
            
            # 构建刷新消息
            refresh_message = {
                'type': 'character_state_refresh',
                'character_id': character_id,
                'timestamp': int(time.time()),
                'message': '角色状态已更新，请刷新显示'
            }
            
            # 广播给所有连接的WebSocket客户端
            await manager.broadcast(json.dumps(refresh_message, ensure_ascii=False))
            print(f"已通过WebSocket通知前端刷新角色状态: {refresh_message}")
            
        except Exception as ws_error:
            print(f"WebSocket通知失败: {ws_error}")
            # WebSocket失败不影响主流程，继续执行
    else:
        print("无角色状态更新，无需通知前端刷新")
    
    print("---Frontend Refresh Agent 完成---")
    return state

# --- 3. 定义路由函数和构建 LangGraph 图 ---
def route_decision(state: AgentState):
    """根据 happening_event_id 的状态路由"""
    if state["happening_event_id"] != -1:
        return "event_happening"
    else:
        return "no_event_happening"

workflow = StateGraph(AgentState)

# 定义所有节点
workflow.add_node("router", router_agent)
workflow.add_node("main_event", main_event_agent)
workflow.add_node("no_main_event_story", no_main_event_story_agent)
workflow.add_node("main_event_happening", main_event_happening_agent)
workflow.add_node("event_happened_story", event_happened_story_agent)
workflow.add_node("frontend_refresh", frontend_refresh_agent)

# 设置入口
workflow.set_entry_point("router")

# 路由器条件边 - 使用正确的路由语法
workflow.add_conditional_edges(
    "router",
    lambda state: "event_happening" if state.get("happening_event_id", -1) != -1 else "no_event_happening",
    {
        "event_happening": "main_event_happening",
        "no_event_happening": "main_event"
    }
)

# main_event 的条件边
def main_event_decision(state: AgentState):
    happening_event_id = state.get("happening_event_id", -1)
    final_output = state.get("final_output", "")
    
    print(f"Main Event Decision: happening_event_id={happening_event_id}, final_output={final_output}")
    
    if happening_event_id == -1 and final_output == "":
        # 无事件且无输出，进入无事件故事流程
        return "no_event"
    elif happening_event_id != -1:
        # 有事件正在进行，直接结束，让下一轮处理事件
        return "event_in_progress"
    else:
        # 有事件，但不需要检定，结束本轮
        return "event_no_skill_check"

workflow.add_conditional_edges(
    "main_event",
    main_event_decision,
    {
        "no_event": "no_main_event_story",
        "event_in_progress": "frontend_refresh",  # 事件正在进行，经过前端刷新后结束
        "event_no_skill_check": "frontend_refresh"  # 有事件，但不需要检定，经过前端刷新后结束
    }
)

# 其他边
workflow.add_edge("no_main_event_story", "frontend_refresh")  # 无事件故事流程，经过前端刷新后结束
workflow.add_edge("main_event_happening", "event_happened_story")
workflow.add_edge("event_happened_story", "frontend_refresh")  # 事件完成故事，经过前端刷新后结束
workflow.add_edge("frontend_refresh", END)  # 前端刷新完成后结束

# 编译工作流
app_langgraph = workflow.compile()

# --- 4. 将 LangGraph 封装成 FastAPI 路由 ---
graph_router = APIRouter()

class ChatRequest(BaseModel):
    input: str
    role: str
    module: Optional[str] = None
    character_id: Optional[str] = None
    happening_event_id: Optional[int] = -1
    
@graph_router.post("/chat")
async def chat_endpoint(request: ChatRequest):
    print(f"接收到请求: role='{request.role}', input='{request.input}'")
    
    if request.role == "KP":
        character_id = get_current_character_id()
        conversation_history = get_conversation_history(character_id)
        
        # 从Redis加载已完成的事件列表
        completed_event_ids = get_completed_event_ids(character_id)
        completed_events = get_completed_events(character_id)
        print(f"从Redis加载已完成事件ID列表: {completed_event_ids}")
        print(f"从Redis加载已完成事件列表: {completed_events}")
        
        # 角色数据信息
        character_data = get_character_data_from_redis(character_id)

        # 从Redis获取当前正在进行的事件ID
        current_happening_event_id = character_data.get("happening_event_id", -1)
        print(f"从Redis获取的当前事件ID: {current_happening_event_id}")

        inputs_for_langgraph = {
            "player_input": request.input,
            "conversation_history": conversation_history,
            "happening_event_id": current_happening_event_id,
            "happening_event_result": 0,
            "happening_event_info": "",
            "final_output": "",
            # 角色数据信息
            "character_info": character_data.get("character_info", {}),
            "character_attributes": character_data.get("character_attributes", {}),
            "character_skills": character_data.get("character_skills", {}),
            "character_derived_attributes": character_data.get("character_derived_attributes", {}),
            "character_background": character_data.get("character_background", "未知"),
            "character_profession": character_data.get("character_profession", "未知"),
            # 角色状态信息
            "character_sanity": character_data.get("character_sanity", 99),
            "character_health": character_data.get("character_health", 99),
            "character_magic": character_data.get("character_magic", 99),
            # 游戏状态信息
            "current_map_id": character_data.get("current_map_id", "1"),
            "skill_check_result_info": {},
            "completed_happened_events": completed_events,
            "completed_happened_event_ids": completed_event_ids,
            # 前端状态管理
            "character_state_updated": False,  # 初始状态为False
            # 环境信息
            "nearby_objects": [],
            "npc_presence": []
        }
        
        try:
            print(f"准备调用LangGraph，输入数据: {inputs_for_langgraph}")
            final_state = await app_langgraph.ainvoke(inputs_for_langgraph)
            print(f"LangGraph执行完成，最终状态: {final_state}")
            
            reply = final_state.get("final_output", "无法生成回复。")
            
            updated_conversation_history = final_state.get("conversation_history", [])
            save_conversation_history(character_id, updated_conversation_history)
            
            # 从最终状态中获取更新后的已完成事件列表，并保存到Redis
            updated_completed_events = final_state.get("completed_happened_events", completed_events)
            updated_completed_event_ids = final_state.get("completed_happened_event_ids", completed_event_ids)
            
            save_completed_events(character_id, updated_completed_events)
            save_completed_event_ids(character_id, updated_completed_event_ids)

            print(f"已保存对话历史，长度: {len(updated_conversation_history)}")
            print(f"已保存已完成事件ID列表，长度: {len(updated_completed_event_ids)}")
            
            new_happening_event_id = final_state.get("happening_event_id", -1)
            print(f"新的事件ID: {new_happening_event_id}")
            
            # 更新Redis中的事件ID
            from redis_manager import update_happening_event_id_in_redis
            update_success = update_happening_event_id_in_redis(character_id, new_happening_event_id)
            if update_success:
                print(f"Redis中的事件ID已更新为: {new_happening_event_id}")
            else:
                print(f"Redis中的事件ID更新失败")

            return {
                "reply": reply,
                "conversation_history": updated_conversation_history,
                "happening_event_id": new_happening_event_id
            }
        except Exception as e:
            print(f"LangGraph 运行出错: {e}")
            print(f"错误类型: {type(e)}")
            import traceback
            print(f"详细错误信息: {traceback.format_exc()}")
            raise HTTPException(status_code=500, detail="LangGraph 运行失败，请检查后端日志。")
    
    else:
        raise HTTPException(status_code=400, detail="未知的角色类型。")