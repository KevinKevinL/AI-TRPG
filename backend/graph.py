# graph.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import TypedDict, List, Dict, Any, Optional
from langgraph.graph import StateGraph, END
import random
import os
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
import skillCheck
import random_event
from character_state import get_current_character_id

# 加载环境变量
load_dotenv()

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

class RouterOutput(BaseModel):
    intents: List[str] = Field(
        description="玩家的意图列表，可以是 'skill_check', 'dialogue', 'info_retrieval' 中的一个或多个。"
    )
    
# --- 2. 定义 Agent 节点函数（保持不变） ---
def router_agent(state: AgentState):
    """..."""
    print("---Router Agent 开始---")
    player_input = state["player_input"].lower()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("请在 .env 文件中设置 OPENAI_API_KEY")

    llm = ChatOpenAI(api_key=api_key, model="gpt-4o-mini", temperature=0)
    llm_with_tools = llm.with_structured_output(RouterOutput)
    system_message = """你是一名游戏中的意图识别助手。你的任务是根据玩家的输入，识别其意图。
    意图列表包括：
    - 'skill_check': 当玩家想要进行某项技能检定时。例如："我要进行力量检定" 或 "我尝试说服他"。
    - 'dialogue': 当玩家想要和npc进行普通的对话时。例如："你好"这样的对话内容，或是玩家有和npc对话的意图。
    - 'info_retrieval': 当玩家试图获取背景信息或物品信息时。例如："告诉我这个地方的历史" 或 "这把剑是什么来头？"。
    - 'random_event': 当玩家的输入可能触发一个随机事件时。请判断玩家是否使用了类似 "探索", "搜索" 或其他可能触发随机事件的词语。

    如果玩家的输入包含多种意图，请返回一个包含所有意图的列表。
    如果无法识别出任何特定意图，请默认返回 ['info_retrieval']。
    """
    
    messages = [SystemMessage(content=system_message), HumanMessage(content=player_input)]
    
    try:
        response = llm_with_tools.invoke(messages)
        intents = response.intents
        if random.random() < 0.98:
            if "random_event" not in intents:
                intents.append("random_event")
        print(f"识别到的意图: {intents}")
        return {"intents": intents}
    except Exception as e:
        print(f"调用 OpenAI API 失败: {e}")
        return {"intents": ["info_retrieval"]}

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
    current_id = get_current_character_id
    print(f"当前角色ID: {current_id}")
    event_desc = random_event.get_random_event_result(get_current_character_id())
    return {"random_event_desc": event_desc}

def rag_retrieval_agent(state: AgentState):
    print("---RAG Retrieval Agent 开始---")
    info = "根据资料，这个NPC是村庄的铁匠。"
    return {"retrieved_info": info}

def story_weaver_agent(state: AgentState):
    print("---Story Weaver Agent 开始---")
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
    return {"final_output": final_output}

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
# 关键改动: 使用 APIRouter() 而不是 FastAPI()
graph_router = APIRouter()

# 定义请求体的 Pydantic 模型，以匹配前端发送的 JSON
class ChatRequest(BaseModel):
    input: str
    role: str
    module: Optional[str] = None
    
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

# 新的统一 API 路由
# 关键改动: 使用 @graph_router.post()
@graph_router.post("/chat")
async def chat_endpoint(request: ChatRequest):
    """
    统一处理 KP 和 NPC 的聊天请求。
    """
    print(f"接收到请求: role='{request.role}', input='{request.input}'")
    
    # 根据 role 参数，分发到不同的处理逻辑
    if request.role == "KP":
        # 这是 KP（守密人）对话，使用 LangGraph 逻辑
        inputs_for_langgraph = {"player_input": request.input}
        try:
            final_state = app_langgraph.invoke(inputs_for_langgraph)
            reply = final_state.get("final_output", "无法生成回复。")
            return {"reply": reply}
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
