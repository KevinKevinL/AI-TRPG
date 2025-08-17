# graph.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import TypedDict, List, Dict, Any, Optional
from langgraph.graph import StateGraph, END
import random
import os
import json
import redis
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
import skillCheck
from intent_recognizer import recognize_intents
import random_event
from character_state import get_current_character_id

# 加载环境变量
load_dotenv()

# 初始化Redis连接
redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

# 对话历史存储的键前缀
CONVERSATION_KEY_PREFIX = "conversation_history:"

# 对话历史Redis操作函数
def get_conversation_history(character_id: str) -> List[Dict[str, str]]:
    """从Redis获取对话历史"""
    try:
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
        key = f"{CONVERSATION_KEY_PREFIX}{character_id}"
        # 设置过期时间为24小时
        redis_client.setex(key, 86400, json.dumps(history, ensure_ascii=False))
    except Exception as e:
        print(f"保存对话历史失败: {e}")

# --- 1. 定义 LangGraph 状态和 Pydantic 模型（保持不变） ---
class AgentState(TypedDict):
    """代表图的当前状态的类。"""
    player_input: str
    intents: List[str]
    npc_response: str
    skill_check_result: str
    random_event_desc: str
    retrieved_info: str
    final_output: str
    character_info: str
    conversation_history: List[Dict[str, str]]  # 对话记录字段，存储用户输入和最终输出

# --- 2. 定义 Agent 节点函数（保持不变） ---
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
    # events = ["附近传来了一声狼嚎。", "你发现了一株稀有的草药。"]
    current_id = get_current_character_id()
    print(f"当前角色ID: {current_id}")
    event_desc = random_event.get_random_event_result(current_id)
    return {"random_event_desc": event_desc}

def rag_retrieval_agent(state: AgentState):
    print("---RAG Retrieval Agent 开始---")
    info = "根据资料，这个NPC是村庄的铁匠。"
    return {"retrieved_info": info}

def story_weaver_agent(state: AgentState):
    print("---Story Weaver Agent 开始---")
    
    # 获取对话历史
    conversation_history = state.get("conversation_history", [])
    
    # 构建包含对话历史的上下文
    context_parts = []
    
    # 添加最近的对话历史（最多保留最近5轮对话）
    if conversation_history:
        recent_history = conversation_history[-5:]  # 只保留最近5轮
        for entry in recent_history:
            if entry.get("user_input"):
                context_parts.append(f"玩家: {entry['user_input']}")
            if entry.get("kp_output"):
                context_parts.append(f"KP: {entry['kp_output']}")
    
    # 添加当前轮次的信息
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
    
    # 更新对话记录
    new_conversation_entry = {
        "user_input": state["player_input"],
        "kp_output": final_output
    }
    
    # 将新的对话记录添加到历史中
    updated_history = conversation_history + [new_conversation_entry]
    
    return {
        "final_output": final_output,
        "conversation_history": updated_history
    }

# --- 3. 定义路由函数和构建 LangGraph 图（保持不变） ---
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

# 定义请求体的 Pydantic 模型，以匹配前端发送的 JSON
class ChatRequest(BaseModel):
    input: str
    role: str
    module: Optional[str] = None
    character_id: Optional[str] = None  # 新增：角色ID，用于标识不同的对话
    
# 专门处理 NPC 聊天的逻辑
async def handle_npc_chat(input: str, role: str) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("请在 .env 文件中设置 OPENAI_API_KEY")

    llm = ChatOpenAI(api_key=api_key, model="gpt-4o-mini", temperature=0.7)
    
    # 构建 NPC 聊天的系统提示
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

# API 路由
@graph_router.post("/chat")
async def chat_endpoint(request: ChatRequest):
    """
    统一处理 KP 和 NPC 的聊天请求。
    """
    print(f"接收到请求: role='{request.role}', input='{request.input}'")
    
    # 根据 role 参数，分发到不同的处理逻辑
    if request.role == "KP":
        # 这是 KP（守密人）对话，使用 LangGraph 逻辑
        
        # 获取角色ID，如果没有提供则使用默认值
        character_id = request.character_id or "default_character"
        
        # 从Redis获取对话历史
        conversation_history = get_conversation_history(character_id)
        print(f"从Redis获取到的对话历史: {conversation_history}")
        
        inputs_for_langgraph = {
            "player_input": request.input,
            "conversation_history": conversation_history
        }
        try:
            final_state = app_langgraph.invoke(inputs_for_langgraph)
            reply = final_state.get("final_output", "无法生成回复。")
            updated_conversation_history = final_state.get("conversation_history", [])
            
            # 保存更新后的对话历史到Redis
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
        # 这是 NPC 对话，使用简单的 LLM 调用逻辑
        try:
            # 这里的 request.role 字段恰好就是 NPC 的名字
            reply = await handle_npc_chat(request.input, request.role)
            return {"reply": reply}
        except Exception as e:
            print(f"NPC 聊天逻辑运行出错: {e}")
            raise HTTPException(status_code=500, detail="NPC 聊天逻辑失败，请检查后端日志。")
    
    else:
        # 如果 role 未知，返回错误
        raise HTTPException(status_code=400, detail="未知的角色类型。")
