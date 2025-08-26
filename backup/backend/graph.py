from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import TypedDict, List, Dict, Any, Optional
from langgraph.graph import StateGraph, END
import random
import os
import json
import ast
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
import skillCheck
from intent_recognizer import recognize_intents
import random_event
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
        key = f"{KEY_EVENTS_KEY_PREFIX}{character_id}"
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
        key = f"{KEY_EVENTS_KEY_PREFIX}{character_id}"
        redis_client.setex(key, 86400, json.dumps(events, ensure_ascii=False))
    except Exception as e:
        print(f"保存已完成事件列表失败: {e}")

def get_completed_event_ids(character_id: str) -> List[int]:
    """从Redis获取已完成的事件ID列表"""
    try:
        redis_client = get_redis_client()
        if not redis_client:
            return []
        key = f"{KEY_EVENTS_KEY_PREFIX}{character_id}"
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
        key = f"{KEY_EVENTS_KEY_PREFIX}{character_id}"
        redis_client.setex(key, 86400, json.dumps(event_ids, ensure_ascii=False))
    except Exception as e:
        print(f"保存已完成事件ID列表失败: {e}")

# 对话历史Redis操作函数
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
        
        # 如果没有对话历史，返回初始对话记录
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
            "kp_output": "夜幕如同黑色的裹尸布一般笼罩下来。你正在阿卡姆郊外一条孤寂的道路上艰难地行驶着。大雨磅礴，闪电撕裂着漆黑的夜空，车辆只能如同爬行般缓慢挪动，以确保前灯能穿透雨幕，让你不至于迷路。"
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
    intents: List[str]
    npc_response: str
    skill_check_result: str
    event_result: str
    retrieved_info: str
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
    completed_happened_events: List[str] # 已完成的剧情事件
    completed_happened_event_ids: List[int] # 已完成的剧情事件id
    
    # 交互历史
    item_inventory: List[Dict[str, Any]]  # 物品清单
    
    # 环境信息
    nearby_objects: List[str]  # 附近物品
    npc_presence: List[str]  # 在场NPCid列表``

# --- 2. 定义 Agent 节点函数 ---
def router_agent(state: AgentState):
    """路由代理，识别玩家意图"""
    intents = recognize_intents(state["player_input"])
    return {"intents": intents}

def npc_dialogue_agent(state: AgentState):
    print("---NPC Dialogue Agent 开始---")
    response = "你好，勇敢的冒险者！"
    return {"npc_response": response}

def skill_check_agent(state: AgentState):
    print("---Skill Check Agent 开始---")
    result = skillCheck.skill_check(state["player_input"])
    return {"skill_check_result": result}

def random_event_agent(state: AgentState):
    print("---Random Event Agent 开始---")
    current_id = get_current_character_id()
    print(f"当前角色ID: {current_id}")
    
    # 获取当前地图ID和已完成事件ID列表
    current_map_id = state.get("current_map_id", "1")
    completed_event_ids = state.get("completed_happened_event_ids", [])
    conversation_history = state.get("conversation_history", [])
    
    print(f"当前地图ID: {current_map_id}")
    print(f"已完成事件ID列表: {completed_event_ids}")
    
    # 调用random_event模块获取事件结果
    event_result = random_event.get_random_event_result(
        current_id, 
        current_map_id, 
        completed_event_ids, 
        conversation_history
    )
    
    return {"event_result": event_result}

async def rag_retrieval_agent(state: AgentState):
    """
    使用 GraphRAG 进行知识检索的代理节点。
    """
    print("---RAG Retrieval Agent 开始---")
    player_input = state["player_input"]
    
    # 直接使用从 rag_engine 模块导入的实例
    if not rag_engine.search_engine:
        print("GraphRAG 引擎未初始化，返回默认信息。")
        return {"retrieved_info": "无法进行知识检索，请检查后端日志。"}

    try:
        #先不使用GraphRAG检索，直接使用地图剧情文本
        #result = await rag_engine.search_engine.search(player_input)
        #retrieved_info = result.response
        retrieved_info = "检索信息"
        #print(f"GraphRAG 检索结果: {retrieved_info[:100]}...")
        
        # 根据 current_map_id 读取对应的地图文本，拼接到检索结果后
        map_id = state.get("current_map_id", "1")
        map_file_path = os.path.join(os.path.dirname(__file__), "map_story_rag", f"{map_id}.txt")
        map_text = ""
        try:
            if os.path.exists(map_file_path):
                with open(map_file_path, "r", encoding="utf-8") as f:
                    map_text = f.read().strip()
            else:
                print(f"未找到地图文本文件: {map_file_path}")
        except Exception as read_err:
            print(f"读取地图文本失败: {read_err}")
            map_text = ""
        
        # 拼接地图文本（若存在）
        if map_text:
            combined_info = f"{retrieved_info}\n\n【地图情报 - {map_id}】\n{map_text}"
        else:
            combined_info = retrieved_info
        
        # 新增：从所有检索结果中过滤掉已完成的事件
        all_key_events = state.get("all_key_events", [])
        completed_key_events = state.get("completed_key_events", [])

        # 使用大模型API过滤地图剧本，避免透露已完成事件
        if map_text and completed_key_events:
            try:
                filter_prompt = f"""
                你是一个剧本内容过滤器。你的任务是根据已完成的事件列表，过滤掉地图剧本中不应该透露给玩家的内容。

                已完成的事件列表：{completed_key_events}

                请分析以下地图剧本内容，并返回一个过滤后的版本。过滤规则：
                1. 如果某个已完成事件在剧本中有详细描述，请将其替换为简略提及并说明已完成该事件
                2. 保持剧本的整体氛围和神秘感
                3. 不要完全删除相关内容，而是用更简洁的方式叙述
                4. 确保过滤后的内容仍然连贯且有意义

                原始地图剧本：
                {map_text}

                请返回过滤后的地图剧本内容："""

                # 调用OpenAI API进行过滤
                api_key = os.getenv("OPENAI_API_KEY")
                if api_key:
                    llm = ChatOpenAI(api_key=api_key, model="gpt-4o-mini", temperature=0.3)
                    messages = [HumanMessage(content=filter_prompt)]
                    response = await llm.ainvoke(messages)
                    filtered_map_text = response.content.strip()
                    print(f"地图剧本过滤完成，原始长度: {len(map_text)}, 过滤后长度: {len(filtered_map_text)}")
                    
                    # 使用过滤后的地图文本
                    if filtered_map_text:
                        combined_info = f"{retrieved_info}\n\n【地图情报 - {map_id}】\n{filtered_map_text}"
                    else:
                        combined_info = f"{retrieved_info}\n\n【地图情报 - {map_id}】\n{map_text}"
                else:
                    print("未设置OPENAI_API_KEY，跳过地图剧本过滤")
                    combined_info = f"{retrieved_info}\n\n【地图情报 - {map_id}】\n{map_text}"
                    
            except Exception as filter_error:
                print(f"地图剧本过滤失败: {filter_error}")
                # 如果过滤失败，使用原始地图文本
                combined_info = f"{retrieved_info}\n\n【地图情报 - {map_id}】\n{map_text}"
        else:
            # 如果没有已完成事件或地图文本，直接拼接
            combined_info = f"{retrieved_info}\n\n【地图情报 - {map_id}】\n{map_text}" if map_text else retrieved_info
        
        # 新增：从所有检索结果中过滤掉已完成的事件
        all_key_events = state.get("all_key_events", [])
        completed_key_events = state.get("completed_key_events", [])

        

        print(f"拼接后的检索结果: {combined_info}")
        return {"retrieved_info": combined_info}
    except Exception as e:
        print(f"GraphRAG 检索失败: {e}")
        return {"retrieved_info": "检索信息时出错，请重试。"}


async def story_weaver_agent(state: AgentState):
    """故事编织代理，整合所有信息并生成智能回复"""
    print("---Story Weaver Agent 开始---")
    
    player_input = state["player_input"]
    conversation_history = state.get("conversation_history", [])
    
    # 构建简化的系统提示
    system_prompt = f"""
        你是一个经验丰富的克苏鲁跑团游戏守密人（KP）。你的任务是根据玩家的行动和所有背景信息，为玩家创造一个沉浸式、符合剧情的叙述回应。

        你的回复必须严格遵守以下规则：
        1. **保持角色一致性**：你的回复必须完全站在 KP 的角度，与玩家对话。不要暴露你是 AI 或任何自动化系统。
        2. **整合信息，而非暴露信息**：将'检索信息'、'技能检定结果'和'随机事件'等作为你的内部知识。不要将这些信息以任何形式直接展示给玩家。你需要根据这些信息来编织新的剧情，生成玩家应该感知的事件和环境描述。
        3. **创造悬念和氛围**：你的回应应该充满克苏鲁跑团的恐怖、悬念和神秘感。善于使用环境描写和心理活动来烘托气氛。
        4. **保持简洁和聚焦**：只提供玩家需要知道的信息，避免冗余。
        5. **根据玩家行动推动剧情**：你的回复应该直接回应玩家的当前行动，并引导他们进入下一个剧情点。请严格按照一步一步的顺序进行叙事，除非玩家已经采取了相应的行动，否则不要假设任何后续事件（如'遭遇艾米利亚'、'艾米利亚上车'等）已经发生。
        6. **避免元信息**：不要在回复中提及'模组'、'KP 指南'、'检定'等只有守密人才懂的词语。
        7. **严格遵守玩家视角**：**除非已完成事件列表中明确包含相关事件（如'艾米利亚的名字已知'），否则你的回复中不得使用NPC的真实姓名或任何玩家角色尚未发现的秘密信息。** 请始终用模糊的称谓（如"那个女人"、"他"）来指代未知的角色。

        以下是已知的剧情事实，请利用它们来判断当前剧情进度，并避免重复已完成的事件：
        已完成的关键事件：{', '.join(state.get('completed_key_events', []) or ['无'])}

        以下是所有你需要用到的玩家和剧情背景信息，你必须根据它们来生成回复：

        玩家角色：{state.get('character_info', {}).get('name', '未知')}，职业：{state.get('character_info', {}).get('profession', '未知')}
        玩家位置：{state.get('current_location', '未知')}
        玩家状态：理智{state.get('character_sanity', 99)}，生命{state.get('character_health', 10)}

        玩家输入：{player_input}
        玩家输入触发的检定结果：{state.get('skill_check_result', '无')}
        本轮发生的剧本事件：{state.get('event_result', '无')}
        剧情检索信息：{state.get('retrieved_info', '无')}

        生成100-200字的克苏鲁风格回复，自然融入所有信息。"""

    try:
        # 调用OpenAI API
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("请在 .env 文件中设置 OPENAI_API_KEY")

        llm = ChatOpenAI(api_key=api_key, model="gpt-4o-mini", temperature=0.7)
        messages = [SystemMessage(content=system_prompt), HumanMessage(content=player_input)]
        response = await llm.ainvoke(messages)
        final_output = response.content
        print(f"AI生成的回复: {final_output}")
        
    except Exception as e:
        print(f"调用AI API失败: {e}")
        final_output = "无法生成回复，请稍后重试。"
    
    # 更新对话记录
    new_conversation_entry = {"user_input": player_input, "kp_output": final_output}
    updated_history = conversation_history + [new_conversation_entry]
    
    return {"final_output": final_output, "conversation_history": updated_history}


# --- 3. 定义路由函数和构建 LangGraph 图 ---
def router_agent_router_function(state: AgentState):
    return state["intents"]

workflow = StateGraph(AgentState)
workflow.add_node("router", router_agent)
workflow.add_node("npc_dialog", npc_dialogue_agent)
workflow.add_node("skill_check", skill_check_agent)
workflow.add_node("random_event", random_event_agent)
workflow.add_node("rag_retrieval", rag_retrieval_agent)
workflow.add_node("story_weaver", story_weaver_agent)

# 设置入口点
workflow.set_entry_point("router")

# 从 router 到 rag_retrieval 改为普通边（始终执行RAG）
workflow.add_edge("router", "rag_retrieval")

# 添加条件边（去掉对 rag 的条件分支）
workflow.add_conditional_edges(
    "router",
    router_agent_router_function,
    {"dialogue": "npc_dialog", "skill_check": "skill_check", "random_event": "random_event"}
)

# 添加边到story_weaver
workflow.add_edge("npc_dialog", "story_weaver")
workflow.add_edge("skill_check", "story_weaver")
workflow.add_edge("random_event", "story_weaver")
workflow.add_edge("rag_retrieval", "story_weaver")
workflow.add_edge("story_weaver", END)


# 编译工作流
app_langgraph = workflow.compile()

# --- 4. 将 LangGraph 封装成 FastAPI 路由 ---
graph_router = APIRouter()

class ChatRequest(BaseModel):
    input: str
    role: str
    module: Optional[str] = None
    character_id: Optional[str] = None
    
async def handle_npc_chat(input: str, role: str) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("请在 .env 文件中设置 OPENAI_API_KEY")

    llm = ChatOpenAI(api_key=api_key, model="gpt-4o-mini", temperature=0.7)
    
    system_message = (
        f"你是一位克苏鲁的呼唤跑团游戏中的 NPC。你的名字叫 {role}。请根据玩家的输入，"
        "以一个普通 NPC 的口吻进行回复，不要暴露你是 AI。你的回复应该简短且符合你的角色定位。"
    )
    
    messages = [
        SystemMessage(content=system_message),
        HumanMessage(content=input),
    ]

    try:
        response = await llm.ainvoke(messages)
        return response.content
    except Exception as e:
        print(f"调用 OpenAI API 失败: {e}")
        raise HTTPException(status_code=500, detail="Failed to get response from AI model.")

    
@graph_router.post("/chat")
async def chat_endpoint(request: ChatRequest):
    print(f"接收到请求: role='{request.role}', input='{request.input}'")
    
    if request.role == "KP":
        character_id = get_current_character_id()
        conversation_history = get_conversation_history(character_id)
        print(f"从Redis获取到的对话历史: {conversation_history}")
        
        # 获取已完成事件列表
        completed_events_list = get_completed_events(character_id)
        completed_event_ids = get_completed_event_ids(character_id)
        print(f"module={request.module}, completed_events_count={len(completed_events_list)}")

        # 从Redis获取角色数据
        character_data = get_character_data_from_redis(character_id)

        # 构建完整的LangGraph输入
        inputs_for_langgraph = {
            "player_input": request.input,
            "conversation_history": conversation_history,
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
            "current_location": character_data.get("current_location", "未知"),
            "current_map_id": character_data.get("current_map_id", "1"),
            # 关键事件
            "completed_happened_events": completed_events_list,
            "completed_happened_event_ids": completed_event_ids
        }
        
        try:
            final_state = await app_langgraph.ainvoke(inputs_for_langgraph)
            reply = final_state.get("final_output", "无法生成回复。")
            updated_conversation_history = final_state.get("conversation_history", [])
            
            # 检查是否有新的事件发生，如果有则更新已完成事件ID列表
            event_result = final_state.get("event_result", "")
            updated_completed_event_ids = completed_event_ids.copy()  # 复制当前列表
            updated_completed_events = completed_events_list.copy()  # 复制当前已完成事件列表
            
            if event_result and event_result != "无":
                try:
                    # 解析事件结果，提取事件ID和事件概括
                    event_data = json.loads(event_result)
                    if "event_id" in event_data:
                        new_event_id = event_data["event_id"]
                        event_summary = event_data.get("event_summary", f"事件{new_event_id}已发生")
                        
                        # 更新事件ID列表
                        if new_event_id not in updated_completed_event_ids:
                            updated_completed_event_ids.append(new_event_id)
                            print(f"新增已完成事件ID: {new_event_id}")
                        
                        # 更新已完成事件概括列表
                        if event_summary not in updated_completed_events:
                            updated_completed_events.append(event_summary)
                            print(f"新增已完成事件概括: {event_summary}")
                        
                        # 保存更新后的事件ID列表和事件概括列表
                        save_completed_event_ids(character_id, updated_completed_event_ids)
                        save_completed_events(character_id, updated_completed_events)
                        
                except json.JSONDecodeError:
                    print(f"无法解析事件结果JSON: {event_result}")
            
            save_conversation_history(character_id, updated_conversation_history)
            print(f"已保存对话历史到Redis: {updated_conversation_history}")
            print(f"当前已完成事件ID列表: {updated_completed_event_ids}")
            print(f"当前已完成事件概括列表: {updated_completed_events}")

            return {
                "reply": reply,
                "conversation_history": updated_conversation_history
            }
        except Exception as e:
            print(f"LangGraph 运行出错: {e}")
            raise HTTPException(status_code=500, detail="LangGraph 运行失败，请检查后端日志。")
            
    elif request.role == "NPC":
        try:
            reply = await handle_npc_chat(request.input, request.role)
            return {"reply": reply}
        except Exception as e:
            print(f"NPC 聊天逻辑运行出错: {e}")
            raise HTTPException(status_code=500, detail="NPC 聊天逻辑失败，请检查后端日志。")
    
    else:
        raise HTTPException(status_code=400, detail="未知的角色类型。")