from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import TypedDict, List, Dict, Any, Optional
from langgraph.graph import StateGraph, END
import random
import os
import json
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

# 对话历史Redis操作函数
def get_conversation_history(character_id: str) -> List[Dict[str, str]]:
    """从Redis获取对话历史"""
    try:
        redis_client = get_redis_client()
        if not redis_client:
            print("Redis客户端不可用，返回空对话历史")
            return []
            
        key = f"{CONVERSATION_KEY_PREFIX}{character_id}"
        data = redis_client.get(key)
        if data:
            return json.loads(data)
        return []
    except Exception as e:
        print(f"获取对话历史失败: {e}")
        return []

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
    random_event_desc: str
    retrieved_info: str
    final_output: str
    conversation_history: List[Dict[str, str]]
    
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
    current_location: str  # 当前位置
    current_map_id: str  # 当前地图ID
    
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
    event_desc = random_event.get_random_event_result(current_id)
    return {"random_event_desc": event_desc}

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
        result = await rag_engine.search_engine.search(player_input)
        retrieved_info = result.response
        print(f"GraphRAG 检索结果: {retrieved_info[:100]}...")
        return {"retrieved_info": retrieved_info}
    except Exception as e:
        print(f"GraphRAG 检索失败: {e}")
        return {"retrieved_info": "检索信息时出错，请重试。"}

def story_weaver_agent(state: AgentState):
    print("---Story Weaver Agent 开始---")
    
    conversation_history = state.get("conversation_history", [])
    
    context_parts = []
    
    if conversation_history:
        recent_history = conversation_history[-5:]
        for entry in recent_history:
            if entry.get("user_input"):
                context_parts.append(f"玩家: {entry['user_input']}")
            if entry.get("kp_output"):
                context_parts.append(f"KP: {entry['kp_output']}")
    
    narrative_parts = []
    if state.get("npc_response"):
        narrative_parts.append(state["npc_response"])
    if state.get("skill_check_result"):
        narrative_parts.append(state["skill_check_result"])
    if state.get("random_event_desc"):
        narrative_parts.append(state["random_event_desc"])
    if state.get("retrieved_info"):
        narrative_parts.append(state["retrieved_info"])
    
    final_output = " ".join(narrative_parts)
    print(f"整合后的输出: {final_output}")
    print(f"对话历史: {conversation_history}")
    
    new_conversation_entry = {
        "user_input": state["player_input"],
        "kp_output": final_output
    }
    
    updated_history = conversation_history + [new_conversation_entry]
    
    return {
        "final_output": final_output,
        "conversation_history": updated_history
    }

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
workflow.set_entry_point("router")
workflow.add_conditional_edges(
    "router",
    router_agent_router_function,
    {"dialogue": "npc_dialog", "skill_check": "skill_check", "random_event": "random_event", "info_retrieval": "rag_retrieval"}
)
workflow.add_edge("npc_dialog", "story_weaver")
workflow.add_edge("skill_check", "story_weaver")
workflow.add_edge("random_event", "story_weaver")
workflow.add_edge("rag_retrieval", "story_weaver")
workflow.add_edge("story_weaver", END)
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
            "character_sanity": character_data.get("character_sanity", 99),
            "character_health": character_data.get("character_health", 10),
            "character_magic": character_data.get("character_magic", 10),
            "current_location": character_data.get("current_location", "未知"),
            "current_map_id": character_data.get("current_map_id", "1"),
            "item_inventory": character_data.get("item_inventory", []),
            "nearby_objects": character_data.get("nearby_objects", []),
            "npc_presence": character_data.get("npc_presence", [])
        }
        
        try:
            final_state = await app_langgraph.ainvoke(inputs_for_langgraph)
            reply = final_state.get("final_output", "无法生成回复。")
            updated_conversation_history = final_state.get("conversation_history", [])
            
            save_conversation_history(character_id, updated_conversation_history)
            print(f"已保存对话历史到Redis: {updated_conversation_history}")
            
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