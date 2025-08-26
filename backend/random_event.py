import json
import random
import asyncio
import re
from typing import List, Dict, Any, Optional

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from dotenv import load_dotenv

# 导入你的数据库管理器
from databaseManager import DatabaseManager

# 加载环境变量
load_dotenv()

# 全局数据库管理器实例
db_manager = DatabaseManager()


def _extract_first_json_object(text: str) -> Optional[dict]:
    """从文本中提取并解析第一个JSON对象，兼容包含```等包裹或前后说明的情况。"""
    if not text:
        return None
    # 去掉常见的markdown代码块围栏
    cleaned = text.strip()
    cleaned = cleaned.replace('```json', '```').strip()
    if cleaned.startswith('```') and cleaned.endswith('```'):
        cleaned = cleaned.strip('`').strip()
    # 直接尝试解析
    try:
        return json.loads(cleaned)
    except Exception:
        pass
    # 用正则提取第一个大括号包裹的JSON片段
    m = re.search(r"\{[\s\S]*\}", cleaned)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            return None
    return None

async def get_random_event_result(
    player_input: str,
    current_map_id: str,
    completed_event_ids: List[int],
    completed_events: List[str],
    conversation_history: List[Dict[str, str]]
) -> str:
    """
    根据当前游戏状态和已完成事件列表，决定下一个发生的事件，并返回结果。
    """
    try:
        # 获取当前地图中所有尚未发生的事件
        query = "SELECT * FROM events WHERE map_id = ? AND happened_result = -1"
        all_pending_events = db_manager.execute_query(query, (current_map_id,))

        if not all_pending_events:
            return json.dumps({
                "event_id": -1,
                "final_kp_narrative": "当前地图没有可触发的主线事件。"
            })

        # 筛选出满足拓扑排序条件的事件
        candidate_events = []
        for event in all_pending_events:
            pre_event_ids_str = event.get("pre_event_ids")
            if pre_event_ids_str:
                pre_event_ids = [int(i) for i in pre_event_ids_str.split(',')]
                if all(id in completed_event_ids for id in pre_event_ids):
                    candidate_events.append(event)
            else:
                candidate_events.append(event)

        if not candidate_events:
            return json.dumps({
                "event_id": -1,
                "final_kp_narrative": "当前没有满足前置条件的主线事件可触发。"
            })
            
        # 仅提供最小必要信息给LLM进行事件选择，避免泄露后续剧情
        candidate_for_llm_select = [
            {"event_id": e["event_id"], "event_info": (e.get("event_info") or "").strip()[:120]}
            for e in candidate_events
        ]

        # 合并为一次调用：选择事件 + 生成叙事
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.2)

        system_prompt = (
            '你是克苏鲁跑团游戏的KP助手。你的任务是根据玩家输入、对话历史和已完成事件，\n'
            '从候选主线事件中“只选择一个事件”，并基于该事件生成本轮的kp_narrative。\n'
            '选择策略：优先选择与玩家当前意图/动作最贴合且与当前剧情连续的事件；当候选均不匹配时才返回 {"event_id": -1}（避免连续多轮不触发）。\n'
            '叙事规则：\n'
            '- 只描述事件发生时的环境与开场，不要给出success或fail的结果；\n'
            '- 可以描写氛围和细节，但不得自行添加新的剧情走向；\n'
            '- 禁止引入事件和对话历史中未出现的“具体实体/地点/物件/宗教/超自然元素”；\n'
            '- 连续性约束：延续上一轮的场景/方式；若必须改变（如车内→徒步），先用一句自然的过渡语交代变化原因；\n'
            '- 语言简洁为宜，同时细节描写要到位，不要故弄玄虚；结尾加一句自然的引导（非命令/非菜单），鼓励玩家继续表达。\n'
            '严格只返回一个JSON（不要使用```、不要添加任何解释或前后缀）：\n'
            '{"event_id": number, "kp_narrative": string, "event_info": string}'
        )

        user_prompt = (
            f'玩家当前输入：{player_input}\n'
            f'对话历史：{json.dumps(conversation_history, ensure_ascii=False)}\n'
            f'已完成主线事件（数量={len(completed_events)}）：{json.dumps(completed_events[-3:], ensure_ascii=False)}\n'
            f'候选主线事件：{json.dumps(candidate_for_llm_select, ensure_ascii=False)}\n'
            '请根据上述候选“只选择一个事件”，并“只基于该事件”生成kp_narrative，不要涉及到其他候选事件的信息；若更适合放缓节奏可返回 {"event_id": -1}。'
        )

        response = await llm.ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ])
        response_content = response.content.strip()
        print(f"LLM原始响应: {response_content}")

        # 解析一次性结果（容错处理```包裹、说明性文本等）
        try:
            llm_result = json.loads(response_content)
        except Exception:
            llm_result = _extract_first_json_object(response_content) or {}

        selected_event_id = int(llm_result.get("event_id", -1)) if isinstance(llm_result, dict) else -1
        final_kp_narrative = llm_result.get("kp_narrative", "") if isinstance(llm_result, dict) else ""
        event_info = llm_result.get("event_info", "") if isinstance(llm_result, dict) else ""
        
        # 如果LLM决定不触发事件
        if selected_event_id == -1:
            return json.dumps({
                "event_id": -1,
                "final_kp_narrative": final_kp_narrative or "无特殊事件发生。",
                "event_info": event_info or "无特殊事件发生。"
            }, ensure_ascii=False)

        # 返回最终结果
        result_dict = {
            "event_id": selected_event_id,
            "final_kp_narrative": final_kp_narrative,
            "event_info": event_info
        }
        return json.dumps(result_dict, ensure_ascii=False)
    
    except Exception as e:
        print(f"random_event 代理出错: {e}")
        return json.dumps({
            "event_id": -1,
            "final_kp_narrative": f"事件处理系统出错：{e}",
            "event_info": "事件处理系统出错。"
        })
