# random_event.py

import json
import random
import asyncio
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

async def get_random_event_result(
    character_id: str,
    current_map_id: str,
    completed_event_ids: List[int],
    conversation_history: List[Dict[str, str]]
) -> str:
    """
    根据当前游戏状态和已完成事件列表，决定下一个发生的事件，并返回结果。
    """
    try:
        # 获取当前角色的数据，用于技能检定
        character_data = db_manager.get_character_data(character_id)

        # 1. 获取当前地图中所有尚未发生的事件
        query = "SELECT * FROM events WHERE map_id = ? AND happened_result = -1"
        all_pending_events = db_manager.execute_query(query, (current_map_id,))

        # 如果没有符合当前地图的待定事件，返回空
        if not all_pending_events:
            return json.dumps({"event_result_info": "当前地图没有可触发的事件。"})

        # 2. 筛选出满足拓扑排序条件的事件
        candidate_events = []
        for event in all_pending_events:
            pre_event_ids_str = event.get("pre_event_ids")
            if pre_event_ids_str:
                pre_event_ids = [int(i) for i in pre_event_ids_str.split(',')]
                # 检查所有前置事件是否都已完成
                if all(id in completed_event_ids for id in pre_event_ids):
                    candidate_events.append(event)
            else:
                # 没有前置事件的事件也算作候选
                candidate_events.append(event)

        # 如果没有符合条件的事件，则返回空结果
        if not candidate_events:
            return json.dumps({"event_result_info": "当前没有满足前置条件的事件。"})

        # 3. 对候选事件进行技能检定（根据你的 skillCheck 模块）
        events_with_checks = []
        for event in candidate_events:
            test_id = event.get("test_required_id")
            check_result = None
            success = False
            # 假设 test_id 映射到某个技能或属性
            if test_id:
                # TODO: 实际的技能检定逻辑
                # 这里我们简化为模拟检定结果
                success = random.random() > 0.5
                skill_name = "未知技能" # 你需要根据 test_id 映射到技能名
                check_result = f"技能检定 [{skill_name}] 结果: {'成功' if success else '失败'}"
            
            events_with_checks.append({
                "event_id": event.get("event_id"),
                "event_info": event.get("event_info"),
                "check_result": check_result,
                "success": success,
                "happened_result": event.get("happened_result", -1)
            })
            
        # 4. 调用 LLM 选择一个最合适的事件发生，并生成事件概括
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.5)
        
        # 构建 LLM 提示，让它同时选择事件和生成概括
        prompt = (
            "你是一个资深的跑团游戏导演。你的任务是根据当前对话的上下文，从一个候选事件列表中，选择一个最合适、最能推动剧情发展的事件来触发，并为该事件生成一个简洁的概括。\n"
            "请严格遵守以下规则：\n"
            "1. **只选择一个事件**：你必须且只能从'候选事件列表'中选择一个事件。\n"
            "2. **考虑上下文**：你的选择应该与'对话历史'和'玩家当前行动'高度相关。\n"
            "3. **考虑检定结果**：如果事件有检定结果，请考虑它是否会为剧情带来有趣的转折。\n"
            "4. **生成事件概括**：为选中的事件生成一个10-20字的事件概括，用过去时态描述已发生的事件。\n"
            "5. **返回格式**：你必须严格按照以下JSON格式返回，不要包含其他任何文本：\n"
            "   {\n"
            '     "selected_event_id": 事件ID数字,\n'
            '     "event_summary": "事件概括文字"\n'
            "   }\n\n"
            f"对话历史：{json.dumps(conversation_history)}\n"
            f"玩家当前行动：{conversation_history[-1]['user_input'] if conversation_history else '无'}\n"
            f"候选事件列表：{json.dumps(events_with_checks, ensure_ascii=False)}\n\n"
            "请返回JSON格式的结果："
        )
        
        try:
            response = await llm.ainvoke([HumanMessage(content=prompt)])
            response_content = response.content.strip()
            print(f"LLM原始响应: {response_content}")
            
            # 解析LLM响应，提取事件ID和概括
            try:
                # 尝试直接解析JSON
                llm_result = json.loads(response_content)
                selected_event_id = int(llm_result["selected_event_id"])
                event_summary = llm_result["event_summary"]
            except (json.JSONDecodeError, KeyError, ValueError) as parse_error:
                print(f"LLM响应解析失败: {parse_error}")
                # 如果解析失败，尝试提取数字作为事件ID，并生成默认概括
                import re
                event_id_match = re.search(r'\d+', response_content)
                if event_id_match:
                    selected_event_id = int(event_id_match.group())
                    event_summary = f"事件{selected_event_id}已发生"
                    print(f"使用正则提取的事件ID: {selected_event_id}")
                else:
                    # 如果连数字都提取不到，随机选择一个事件
                    selected_event_id = random.choice([e["event_id"] for e in candidate_events])
                    event_summary = f"事件{selected_event_id}已发生"
                    print(f"随机选择的事件ID: {selected_event_id}")
            
            print(f"最终选择的事件ID: {selected_event_id}")
            print(f"生成的事件概括: {event_summary}")
            
        except Exception as llm_error:
            print(f"LLM调用失败: {llm_error}")
            # 如果LLM调用失败，随机选择一个事件
            selected_event = random.choice(candidate_events)
            selected_event_id = selected_event["event_id"]
            event_summary = f"事件{selected_event_id}已发生"
            print(f"LLM失败，随机选择事件ID: {selected_event_id}")
        
        # 5. 更新数据库和返回结果
        selected_event = next((e for e in candidate_events if e["event_id"] == selected_event_id), None)
        if not selected_event:
            return json.dumps({"event_result_info": "未能选择一个有效的事件。"})
            
        success_flag = next((e['success'] for e in events_with_checks if e['event_id'] == selected_event_id), False)
        
        final_result_info = ""
        if success_flag:
            final_result_info = selected_event["success_result_info"]
        else:
            final_result_info = selected_event["fail_result_info"]

        # 更新事件状态到数据库
        happened_result_code = 1 if success_flag else 0
        update_query = "UPDATE events SET happened_result = ? WHERE event_id = ?"
        db_manager.execute_query(update_query, (happened_result_code, selected_event_id))

        # TODO: 每次事件发生后，将 event_id 添加到 completed_event_ids 中，以便下一次调用
        # 这里需要你手动在 graph.py 的 chat_endpoint 函数中处理
        
        result_dict = {
            "event_id": selected_event_id,
            "event_info": selected_event.get("event_info"),
            "happened_result": happened_result_code,
            "result_narrative": final_result_info,
            "event_summary": event_summary  # 事件概括
        }
        
        return json.dumps(result_dict, ensure_ascii=False)
    
    except Exception as e:
        print(f"random_event 代理出错: {e}")
        return json.dumps({"event_result_info": f"事件处理系统出错：{e}"})
