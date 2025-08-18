# intent_recognizer.py

import os
import random
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field
from typing import List

class RouterOutput(BaseModel):
    intents: List[str] = Field(
        description="玩家的意图列表，可以是 'skill_check', 'dialogue', 'info_retrieval' 中的一个或多个。"
    )

def recognize_intents(player_input: str) -> List[str]:
    """
    识别玩家输入的意图
    参数: player_input - 玩家的输入文本
    返回: 意图列表
    """
    print("---Router Agent 开始---")
    player_input = player_input.lower()
    
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
        
        # 随机添加随机事件（10%概率）
        if random.random() < 0.1:
            if "random_event" not in intents:
                intents.append("random_event")
        
        print(f"识别到的意图: {intents}")
        return intents
        
    except Exception as e:
        print(f"调用 OpenAI API 失败: {e}")
        return ["info_retrieval"]
