# graph.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import TypedDict, List, Dict, Any, Optional
from langgraph.graph import StateGraph, END
import json
import asyncio
import random

# --- LLM and Langchain Imports ---
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

# --- Local Module Imports ---
from databaseManager import db_manager
from character_state import get_current_character_id
from memory_manager import memory_manager
from map_movement import map_movement_manager
from redis_manager import (
    get_world_state, save_world_state,
    get_map_state, save_map_state,
    get_session_state, save_session_state,
    get_character_sheet,
    get_conversation_history, save_conversation_history,
    get_completed_event_ids, save_completed_event_ids,
    apply_state_changes, apply_map_state_changes
)
import player_action_parser
from player_action_parser import get_skill_value_from_sheet # 导入新工具函数

class AgentState(TypedDict):
    player_input: str
    final_output: str
    character_id: str
    character_sheet: Dict[str, Any]
    session_state: Dict[str, Any]
    world_state: Dict[str, Any]
    map_state: Dict[str, Any]
    conversation_history: List[Dict[str, str]]
    completed_events: List[int]
    active_npcs: List[Dict[str, Any]]
    interactable_objects: List[Dict[str, Any]]
    player_action: Dict[str, Any]
    triggered_event: Optional[Dict[str, Any]]
    skill_check_result: Optional[Dict[str, Any]]
    npc_reactions: List[Dict[str, Any]]
    pending_event_data: Optional[Dict[str, Any]]
    turn_context_summary: str

def check_preconditions(event: Dict[str, Any], state: AgentState) -> bool:
    pre_event_ids_str = event.get('pre_event_ids')
    if pre_event_ids_str:
        try:
            pre_event_ids = json.loads(pre_event_ids_str)
            if not all(pid in state['completed_events'] for pid in pre_event_ids):
                return False
        except (json.JSONDecodeError, TypeError):
            return False

    if not event.get('preconditions'):
        return True
    
    try:
        preconditions = json.loads(event['preconditions'])
    except (json.JSONDecodeError, TypeError):
        return False

    if 'player_action' in preconditions:
        action = state.get('player_action', {})
        for key, expected_value in preconditions['player_action'].items():
            if action.get(key) != expected_value:
                return False
                
    if 'agent_state' in preconditions:
        agent_reqs = preconditions['agent_state']
        target_session = state['session_state']
        try:
            target_id = agent_reqs.get('agent_id')
            if target_id and target_id != 'player':
                target_session = get_session_state(target_id) or {}
        except Exception:
            pass
        for key, expected_value in agent_reqs.items():
            if key == 'agent_id': continue
            session_key = 'current_map_id' if key == 'current_location_id' else key
            if target_session.get(session_key) != expected_value:
                return False
        
    return True

async def orchestrator_agent(state: AgentState):
    print("--- 节点: Orchestrator ---")
    print(f"[Orchestrator] 输入: '{state['player_input']}' | 角色: {state['character_id']}")
    print(f"[Orchestrator] session_state: {state['session_state']}")
    print(f"[Orchestrator] map_state 初始: {state['map_state']}")
    map_state = state['map_state']
    
    npc_ids = map_state.get('npcs', [])
    print(f"[Orchestrator] 从 map_state 读取 NPC IDs: {npc_ids}")
    state['active_npcs'] = [get_character_sheet(npc_id).get('info', {}) for npc_id in npc_ids if get_character_sheet(npc_id)]
    print(f"[Orchestrator] active_npcs 加载完成: {[n.get('id') for n in state['active_npcs']]}")
    
    objects_state = map_state.get('objects', {})
    print(f"[Orchestrator] 从 map_state 读取 Objects: keys={list(objects_state.keys())}")
    state['interactable_objects'] = []
    for obj_id, obj_state in objects_state.items():
        obj_info = db_manager.execute_query("SELECT object_name FROM interactable_objects WHERE object_id = ?", (obj_id,))
        obj_name = obj_info[0]['object_name'] if obj_info else f"物品{obj_id}"
        state['interactable_objects'].append({"object_id": obj_id, "object_name": obj_name})
    print(f"[Orchestrator] interactable_objects: {state['interactable_objects']}")

    state['player_action'] = await player_action_parser.parse_player_action(
        state['player_input'], state['active_npcs'], state['interactable_objects']
    )
    print(f"[Orchestrator] 解析到的玩家意图: {state['player_action']}")

    # 先检查当前地图的事件触发条件
    if not state['session_state'].get('pending_check_event_id'):
        current_map_id = state['session_state'].get('current_map_id', 1)
        all_events = db_manager.execute_query("SELECT * FROM events WHERE map_id = ?", (current_map_id,))
        print(f"[Orchestrator] 地图 {current_map_id} 上的所有事件: {[e['event_id'] for e in all_events]}")
        
        if all_events:
            # 显示每个事件的详细信息
            for event in all_events:
                event_id = event['event_id']
                event_info = event['event_info']
                if_unique = event.get('if_unique', 0)
                is_completed = event_id in state['completed_events']
                preconditions_met = check_preconditions(event, state)
                
                print(f"[Orchestrator] 事件 {event_id}: {event_info}")
                print(f"  - 唯一性: {if_unique} (已完成: {is_completed})")
                print(f"  - 前置条件满足: {preconditions_met}")
                if not preconditions_met:
                    try:
                        preconditions = json.loads(event.get('preconditions', '{}'))
                        print(f"  - 前置条件详情: {preconditions}")
                    except:
                        print(f"  - 前置条件详情: {event.get('preconditions', '无')}")
            
            candidate_events = [
                event for event in all_events
                if not (event.get('if_unique') and event['event_id'] in state['completed_events'])
                and check_preconditions(event, state)
            ]
            
            print(f"[Orchestrator] 符合条件的候选事件: {[e['event_id'] for e in candidate_events]}")
            
            if candidate_events:
                state['triggered_event'] = candidate_events[0]
                print(f"[Orchestrator] 事件已触发: {candidate_events[0]['event_id']} - {candidate_events[0]['event_info']}")
            else:
                print("[Orchestrator] 本回合无可触发事件，尝试软性判断...")
                
                # 软性判断：让LLM判断是否有事件应该被触发
                soft_candidate = await soft_check_event_trigger(state, all_events)
                if soft_candidate:
                    state['triggered_event'] = soft_candidate
                    print(f"[Orchestrator] 软性判断触发事件: {soft_candidate['event_id']} - {soft_candidate['event_info']}")
                else:
                    print("[Orchestrator] 软性判断也无事件可触发")
        else:
            print(f"[Orchestrator] 地图 {current_map_id} 上没有事件")
    else:
        print(f"[Orchestrator] 发现挂起检定 pending_check_event_id={state['session_state'].get('pending_check_event_id')}")

    # 如果没有事件触发，才处理移动意图
    if not state.get('triggered_event') and state['player_action'].get('intent') == 'move' and state['player_action'].get('target_location_id'):
        target_map_id = state['player_action']['target_location_id']
        print(f"[Orchestrator] 检测到移动意图，目标地图: {target_map_id}")
        
        # 执行移动
        if map_movement_manager.move_character_to_map(state['character_id'], target_map_id):
            # 移动成功，更新地图状态
            new_map_id = target_map_id
            state['session_state']['current_map_id'] = new_map_id
            state['map_state'] = get_map_state(new_map_id)
            
            # 重新加载新地图的NPC和对象
            npc_ids = state['map_state'].get('npcs', [])
            state['active_npcs'] = [get_character_sheet(npc_id).get('info', {}) for npc_id in npc_ids if get_character_sheet(npc_id)]
            
            objects_state = state['map_state'].get('objects', {})
            state['interactable_objects'] = []
            for obj_id, obj_state in objects_state.items():
                obj_info = db_manager.execute_query("SELECT object_name FROM interactable_objects WHERE object_id = ?", (obj_id,))
                obj_name = obj_info[0]['object_name'] if obj_info else f"物品{obj_id}"
                state['interactable_objects'].append({"object_id": obj_id, "object_name": obj_name})
            
            print(f"[Orchestrator] 移动完成，新地图: {new_map_id}")
            print(f"[Orchestrator] 新地图NPC: {[n.get('id') for n in state['active_npcs']]}")
            print(f"[Orchestrator] 新地图对象: {state['interactable_objects']}")
        else:
            print(f"[Orchestrator] 移动到地图 {target_map_id} 失败")

    
    # 如果是移动意图，添加移动描述
    if state['player_action'].get('intent') == 'move' and state['player_action'].get('target_location_id'):
        movement_desc = map_movement_manager.get_movement_description(
            state['character_id'], 
            state['player_action']['target_location_id']
        )
        state['turn_context_summary'] = f"玩家的行动是：'{state['player_input']}'。\n{movement_desc}\n"
    else:
        state['turn_context_summary'] = f"玩家的行动是：'{state['player_input']}'。\n"
    
    return state

async def resolve_check_agent(state: AgentState):
    print("--- 节点: Resolve Check ---")
    event_id = state['session_state']['pending_check_event_id']
    print(f"[Resolve] 待解决事件ID: {event_id}")
    event_data = db_manager.execute_query("SELECT * FROM events WHERE event_id = ?", (event_id,))[0]
    state['pending_event_data'] = event_data
    
    effects = json.loads(event_data['effects'])
    check_info = effects['skill_check']
    print(f"[Resolve] 检定信息: {check_info}")
    
    char_id_to_check = state['character_id'] if check_info.get('character_id', -1) == -1 else check_info['character_id']

    result = player_action_parser.check_skill_directly(
        char_id_to_check, check_info['skill_id'], check_info['difficulty']
    )
    state['skill_check_result'] = result
    print(f"[Resolve] 检定结果: {result}")
    
    outcome_key = 'success' if result.get('success') else 'failure'
    outcome_narrative = effects.get('outcomes', {}).get(outcome_key, {}).get('narrative', '')
    if outcome_narrative:
        state['turn_context_summary'] += f"事件的结果是：{outcome_narrative}\n"
    
    state['session_state']['pending_check_event_id'] = None
    return state

async def setup_suspense_agent(state: AgentState):
    print("--- 节点: Setup Suspense ---")
    event = state['triggered_event']
    print(f"[Suspense] 设置悬念事件ID: {event.get('event_id') if event else None}")
    state['session_state']['pending_check_event_id'] = event['event_id']
    effects = json.loads(event['effects'])
    state['final_output'] = effects['outcomes']['suspense_narrative']
    print(f"[Suspense] 输出悬念文本长度: {len(state['final_output'])}")
    return state
    
async def npc_loop_agent(state: AgentState):
    """
    NPC处理循环：实现动态、有序的对抗感知。
    """
    print("--- 节点: NPC Loop ---")
    active_npcs_info = state.get('active_npcs', [])
    print(f"[NPC] 本回合NPC数量: {len(active_npcs_info)}")
    print(f"[NPC] active_npcs_info 详细内容: {active_npcs_info}")
    if not active_npcs_info:
        print("[NPC] 没有活跃NPC，返回空反应列表")
        state['npc_reactions'] = []
        return state

    all_reactions = []
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)
    
    def get_dex(npc_info):
        sheet = get_character_sheet(npc_info.get('id'))
        return sheet.get('attributes', {}).get('dexterity', 50)
    
    sorted_npcs = sorted(active_npcs_info, key=get_dex, reverse=True)
    print(f"[NPC Loop] 行动顺序: {[npc.get('name') for npc in sorted_npcs]}")
    print(f"[NPC Loop] 排序后的NPC列表: {sorted_npcs}")
    
    public_context = state['turn_context_summary']
    print(f"[NPC Loop] public_context: {public_context}")
    private_actions_this_turn = []
    
    for npc_info in sorted_npcs:
        npc_id = npc_info.get('id')
        npc_name = npc_info.get('name')
        print(f"[NPC Loop] 处理NPC: id={npc_id}, name={npc_name}")
        if not npc_id or not npc_name: 
            print(f"[NPC Loop] 跳过无效NPC: id={npc_id}, name={npc_name}")
            continue

        perception_context = ""
        observer_sheet = get_character_sheet(npc_id)
        observer_investigate = get_skill_value_from_sheet(observer_sheet, 'investigate')

        for private_action in private_actions_this_turn:
            actor_sheet = get_character_sheet(private_action['npc_id'])
            actor_stealth = get_skill_value_from_sheet(actor_sheet, 'stealth')
            
            dice_roll = random.randint(1, 100)
            if dice_roll <= observer_investigate and dice_roll > actor_stealth / 2:
                perception_context += f"[你察覺到 {private_action['npc_name']} 似乎在暗中{private_action['reaction'].replace('我', '').replace('说：', '低语了些什么...')}]\n"
                print(f"[Perception][NPC] {npc_name} 成功察觉到 {private_action['npc_name']} 的行动")

        # 加载NPC的短期记忆和长期记忆
        memory_data = memory_manager.get_npc_memories_for_context(npc_id)
        memory_context = ""
        
        if memory_data['short_term'] or memory_data['long_term']:
            memory_context = "--- 你的记忆 ---\n"
            
            # 短期记忆（最近的）
            if memory_data['short_term']:
                memory_context += "【短期记忆】\n"
                for memory in memory_data['short_term'][:3]:  # 只显示最近3条
                    memory_context += f"• {memory['content']}\n"
                memory_context += "\n"
            
            # 长期记忆（相关的）
            if memory_data['long_term']:
                memory_context += "【长期记忆】\n"
                for memory in memory_data['long_term']:
                    similarity = memory.get('similarity', 0)
                    memory_context += f"• {memory['content']} (相关度: {1-similarity:.2f})\n"
        
        full_context_for_npc = public_context
        if perception_context:
            full_context_for_npc += "--- 你额外察觉到的情况 ---\n" + perception_context
        if memory_context:
            full_context_for_npc += memory_context

        print(f"[NPC Loop] 给 {npc_name} 的完整上下文: {full_context_for_npc}")
        print(f"[NPC Loop] 开始调用LLM生成 {npc_name} 的反应...")

        system_prompt = f"""
        你正在扮演NPC：{npc_name}。
        你的当前状态是：'{npc_info.get('status', '正常')}'，你的目标是：'{npc_info.get('current_goal', '无')}'。
        根据以下情景，以第一人称视角做出符合你个性的反应。
        
        你的回应必须是严格的JSON格式，包含以下字段：
        - "visibility": "public" 或 "private"
        - "dialogue": "你要说的话"
        - "action": "你要做的动作"
        - "new_status": "新状态"
        - "new_goal": "新目标"
        
        【visibility 判断规则】：
        - "public": 基本信息、直接回答、明显的行为动作、对当前情况的反应
        - "private": 内心想法、秘密计划、暗中观察、不想让别人知道的行动
        
        示例：
        - 正常行动、普通对话 → "public"
        - 表达恐惧、寻求帮助 → "public"
        - 内心独白、秘密计划 → "private"
        - 暗中观察、偷偷行动 → "private"
        
        示例格式：
        {{"visibility": "public", "dialogue": "天哪！", "action": "惊恐地后退", "new_status": "受惊", "new_goal": "寻求安全"}}
        
        注意：必须返回有效的JSON，不要有任何其他文字。
        """
        response = await llm.ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"当前情景: {full_context_for_npc}")
        ])

        try:
            print(f"[NPC Loop] {npc_name} 的LLM原始回应: {response.content}")
            npc_response = json.loads(response.content)
            print(f"[NPC] {npc_id} 模型回应: {npc_response}")
            db_manager.update_npc_state(npc_id, npc_response.get('new_status'), npc_response.get('new_goal'))
            
            reaction_text = ""
            if npc_response.get('dialogue'): reaction_text += f'说：“{npc_response["dialogue"]}”'
            if npc_response.get('action'): reaction_text += f' {npc_response["action"]}'
            
            if reaction_text:
                reaction_entry = {
                    "npc_id": npc_id, "npc_name": npc_name, 
                    "reaction": reaction_text.strip(),
                    "visibility": npc_response.get("visibility", "public")
                }
                all_reactions.append(reaction_entry)

                if reaction_entry["visibility"] == "public":
                    public_context += f"{npc_name}{reaction_text}\n"
                else:
                    private_actions_this_turn.append(reaction_entry)
            
            # 保存当前的观察和反应到短期记忆
            current_observation = f"我观察到以下情景: [玩家的行动是：'{state.get('player_input', '')}'。{public_context.split('玩家的行动是：')[1] if '玩家的行动是：' in public_context else ''}]，并做出了反应: {reaction_text}"
            
            context = {
                "player_input": state.get('player_input', ''),
                "npc_reaction": reaction_text,
                "visibility": npc_response.get("visibility", "public"),
                "turn_context": public_context  # 只包含当前回合的公共上下文
            }
            
            # 添加到短期记忆（Redis），自动触发压缩检查
            memory_manager.add_npc_memory(
                character_id=npc_id,
                memory_text=current_observation,
                context=context
            )

        except (json.JSONDecodeError, KeyError) as e:
            print(f"解析NPC {npc_id} 的回应失败: {e}")
            print(f"[NPC Loop] {npc_name} 的回应解析失败，跳过此NPC")

    state['npc_reactions'] = all_reactions
    print(f"[NPC] 本回合生成反应数量: {len(all_reactions)}")
    return state

async def narrative_synthesizer_agent(state: AgentState):
    print("--- 节点: Narrative Synthesizer ---")
    final_narrative = state['turn_context_summary']
    event_to_complete = None
    
    def process_event_effects(outcome_data):
        nonlocal final_narrative
        if 'narrative' in outcome_data: final_narrative = outcome_data['narrative'] + "\n"
        elif 'narrative_injection' in outcome_data: final_narrative += outcome_data['narrative_injection'] + "\n"

        if 'state_changes' in outcome_data:
            print(f"[Narrative] 应用玩家状态更改: {outcome_data['state_changes']}")
            apply_state_changes(state['character_id'], outcome_data['state_changes'])
        if 'npc_state_change' in outcome_data:
            print(f"[Narrative] 应用NPC状态更改: {outcome_data['npc_state_change']}")
            for change in outcome_data['npc_state_change']: db_manager.update_npc_state(change['character_id'], new_status=change.get('new_status'))
        if 'world_state_change' in outcome_data:
            print(f"[Narrative] 应用世界状态更改: {outcome_data['world_state_change']}")
            state['world_state'].update(outcome_data['world_state_change'])
        if 'map_state_change' in outcome_data:
            print(f"[Narrative] 应用地图状态更改: {outcome_data['map_state_change']}")
            # map_state_change 是一个字典，需要包装成列表
            apply_map_state_changes([outcome_data['map_state_change']])
            # 同步更新state中的map_state，确保最终保存的是最新数据
            current_map_id = state['session_state'].get('current_map_id', 1)
            state['map_state'] = get_map_state(current_map_id)
            print(f"[Narrative] 已同步更新state中的map_state: {state['map_state']}")
        if 'object_state_change' in outcome_data:
            print(f"[Narrative] 应用物品状态更改: {outcome_data['object_state_change']}")
            for change in outcome_data['object_state_change']:
                obj_id = str(change['object_id'])
                if obj_id in state['map_state']['objects']: state['map_state']['objects'][obj_id].update(change['set_state'])

    if state.get('skill_check_result') and state.get('pending_event_data'):
        event_data = state['pending_event_data']
        event_to_complete = event_data
        effects = json.loads(event_data['effects'])
        outcome_key = 'success' if state['skill_check_result'].get('success') else 'failure'
        print(f"[Narrative] 处理检定事件 {event_data.get('event_id')} 的分支: {outcome_key}")
        process_event_effects(effects['outcomes'][outcome_key])
    elif state.get('triggered_event'):
        event = state['triggered_event']
        event_to_complete = event
        print(f"[Narrative] 处理即时事件 {event.get('event_id')}")
        process_event_effects(json.loads(event['effects']))

    for reaction in state.get('npc_reactions', []):
        if reaction.get("visibility", "public") == "public":
            final_narrative += f"{reaction['npc_name']}{reaction['reaction']}\n"
            
    player_sheet = state['character_sheet']
    player_investigate = get_skill_value_from_sheet(player_sheet, 'investigate')
    for reaction in state.get('npc_reactions', []):
        if reaction.get("visibility") == "private":
            actor_sheet = get_character_sheet(reaction['npc_id'])
            actor_stealth = get_skill_value_from_sheet(actor_sheet, 'stealth')
            dice_roll = random.randint(1, 100)
            if dice_roll <= player_investigate and dice_roll > actor_stealth / 2:
                perception_narrative = f"你察觉到了一些异样：{reaction['npc_name']}似乎{reaction['reaction'].replace('我', '在').replace('说：', '低声说了些什么……')}\n"
                final_narrative += perception_narrative
                print(f"[Perception][Player] 成功察觉到 {reaction['npc_name']} 的行动 (掷骰:{dice_roll} vs 调查:{player_investigate})")

    state['final_output'] = final_narrative.strip() or "一切如常。"
    print(f"[Narrative] 最终叙事长度: {len(state['final_output'])}")

    if event_to_complete and event_to_complete.get('if_unique'):
        if event_to_complete['event_id'] not in state['completed_events']:
            state['completed_events'].append(event_to_complete['event_id'])
            print(f"[Narrative] 记录唯一事件完成: {event_to_complete['event_id']}")

    state['conversation_history'].append({"role": "user", "content": state['player_input']})
    state['conversation_history'].append({"role": "assistant", "content": state['final_output']})
    return state

workflow = StateGraph(AgentState)
workflow.add_node("orchestrator", orchestrator_agent)
workflow.add_node("resolve_check", resolve_check_agent)
workflow.add_node("setup_suspense", setup_suspense_agent)
workflow.add_node("npc_loop", npc_loop_agent)
workflow.add_node("narrative_synthesizer", narrative_synthesizer_agent)
workflow.set_entry_point("orchestrator")

def event_logic_router(state: AgentState):
    print(f"[Router] 路由决策开始...")
    print(f"[Router] pending_check_event_id: {state['session_state'].get('pending_check_event_id')}")
    
    if state['session_state'].get('pending_check_event_id'): 
        print(f"[Router] 有挂起检定，路由到: resolve_check")
        return "resolve_check"
    
    event = state.get('triggered_event')
    print(f"[Router] 触发的事件: {event}")
    
    if event:
        try:
            effects = json.loads(event.get('effects', '{}'))
            skill_check_required = effects.get('skill_check', {}).get('required', False)
            print(f"[Router] 事件 {event.get('event_id')} 需要技能检定: {skill_check_required}")
            if skill_check_required: 
                print(f"[Router] 路由到: setup_suspense")
                return "setup_suspense"
        except Exception as e:
            print(f"[Router] 解析事件effects失败: {e}")
        
    print(f"[Router] 默认路由到: npc_loop")
    return "npc_loop"

workflow.add_conditional_edges(
    "orchestrator", event_logic_router,
    {"resolve_check": "resolve_check", "setup_suspense": "setup_suspense", "npc_loop": "npc_loop"}
)
# resolve_check 跑完进入 NPC -> 叙事 -> END
workflow.add_edge("resolve_check", "npc_loop")
workflow.add_edge("npc_loop", "narrative_synthesizer")
# setup_suspense 直接结束一回合
workflow.add_edge("setup_suspense", END)
# 叙事结束
workflow.add_edge("narrative_synthesizer", END)
app_langgraph = workflow.compile()

graph_router = APIRouter()
class ChatRequest(BaseModel):
    input: str

@graph_router.post("/chat")
async def chat_endpoint(request: ChatRequest):
    character_id = get_current_character_id()
    if not character_id: raise HTTPException(status_code=400, detail="没有角色已加载。")
    
    session_state = get_session_state(character_id)
    current_map_id = session_state.get('current_map_id', 1)
    print(f"\n{'='*20} [ 新回合开始 ] {'='*20}")
    print(f"[Chat] 请求输入: '{request.input}' | 角色: {character_id} | 地图: {current_map_id}")
    
    initial_state = AgentState(
        player_input=request.input, character_id=character_id,
        character_sheet=get_character_sheet(character_id),
        session_state=session_state, world_state=get_world_state(),
        map_state=get_map_state(current_map_id),
        conversation_history=get_conversation_history(character_id),
        completed_events=get_completed_event_ids(character_id),
        final_output="", active_npcs=[], interactable_objects=[], player_action={},
        triggered_event=None, skill_check_result=None, npc_reactions=[], 
        pending_event_data=None, turn_context_summary=""
    )
    try:
        player_action_parser.set_event_loop(asyncio.get_running_loop())
        final_state = await app_langgraph.ainvoke(initial_state)
        
        print(f"[Chat] 保存状态: world_state_keys={list(final_state['world_state'].keys())}")
        print(f"[Chat] 保存状态: map_state_npcs={final_state['map_state'].get('npcs', [])} objects={list(final_state['map_state'].get('objects', {}).keys())}")
        print(f"[Chat] 保存状态: session_state={final_state['session_state']}")
        print(f"[Chat] 保存状态: completed_events={final_state['completed_events']}")
        
        save_world_state(final_state['world_state'])
        save_map_state(current_map_id, final_state['map_state'])
        save_session_state(character_id, final_state['session_state'])
        save_conversation_history(character_id, final_state['conversation_history'])
        save_completed_event_ids(character_id, final_state['completed_events'])
        
        print(f"[Chat] 回复长度: {len(final_state.get('final_output', ''))}")
        print(f"{'='*20} [ 回合结束 ] {'='*20}\n")
        return {"reply": final_state.get("final_output", "系统错误")}
    except Exception as e:
        import traceback
        print(f"LangGraph 运行出错: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="LangGraph 运行失败。")


async def soft_check_event_trigger(state: AgentState, all_events: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    软性判断：当硬性前置条件都不满足时，让LLM判断是否有事件应该被触发
    """
    try:
        from langchain_openai import ChatOpenAI
        from langchain_core.messages import SystemMessage, HumanMessage
        
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.1)
        
        # 过滤掉已完成且唯一的事件
        available_events = [
            event for event in all_events
            if not (event.get('if_unique') and event['event_id'] in state['completed_events'])
        ]
        
        if not available_events:
            return None
            
        # 构建事件信息
        events_info = []
        for event in available_events:
            event_desc = f"事件{event['event_id']}: {event['event_info']}"
            if event.get('preconditions'):
                try:
                    preconditions = json.loads(event['preconditions'])
                    event_desc += f" (前置条件: {preconditions})"
                except:
                    pass
            events_info.append(event_desc)
        
        events_text = "\n".join(events_info)
        
        system_prompt = f"""
        你是一个COC跑团的智能事件判断器。根据玩家的行动和当前状态，判断是否有事件应该被触发。

        当前玩家行动: {state.get('player_action', {})}
        当前状态: 地图ID={state['session_state'].get('current_map_id')}, 载具ID={state['session_state'].get('current_vehicle_id')}

        可用事件列表:
        {events_text}

        【重要】请严格按照以下标准判断是否触发事件：

        1. **语义匹配度要求**：
           - 玩家意图与事件描述必须有高度语义相似性（80%以上匹配）
           - 不能因为"有点相似"就触发，必须是"非常相似"或"几乎一致"

        2. **状态兼容性**：
           - 当前状态必须与事件要求的状态高度兼容
           - 如果事件要求特定状态（如载具ID、位置等），当前状态必须基本满足

        3. **逻辑合理性**：
           - 事件触发必须符合游戏逻辑和剧情发展
           - 不能为了触发而触发

        4. **触发阈值**：
           - 只有当玩家行动与事件描述达到"几乎可以确定要触发"的程度时才触发
           - 如果存在任何明显的不匹配，就不应该触发

        示例判断：
        - "我想回忆附近有什么地方" → 事件5（回忆避难所）： 高度匹配，应该触发
        - "让我看看这个挂坠" → 事件8（观察挂坠）： 高度匹配，应该触发
        - "我想开车" → 事件1（遭遇艾米利亚）： 语义不匹配，不应触发
        - "我想聊天" → 任何事件： 过于宽泛，不应触发

        如果认为有事件应该触发，返回JSON格式：
        {{"should_trigger": true, "event_id": 事件ID, "reason": "触发原因", "confidence": "高/中/低"}}
        
        如果认为没有事件应该触发，返回：
        {{"should_trigger": false, "reason": "无合适事件或匹配度不足"}}
        
        严格只返回JSON格式。
        """
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"玩家输入: {state.get('player_input', '')}")
        ]
        
        response = await llm.ainvoke(messages)
        
        try:
            result = json.loads(response.content)
            if result.get('should_trigger') and result.get('event_id'):
                # 检查置信度，只接受高置信度的触发
                confidence = result.get('confidence', '低')
                if confidence in ['高', '中']:
                    # 找到对应的事件
                    target_event = next((e for e in available_events if e['event_id'] == result['event_id']), None)
                    if target_event:
                        print(f"[Soft Check] LLM判断应该触发事件 {result['event_id']}: {result.get('reason', '无原因')} (置信度: {confidence})")
                        return target_event
                else:
                    print(f"[Soft Check] LLM判断置信度过低({confidence})，拒绝触发事件 {result['event_id']}")
            else:
                print(f"[Soft Check] LLM判断无事件应触发: {result.get('reason', '无原因')}")
        except json.JSONDecodeError:
            print(f"[Soft Check] LLM回应JSON解析失败: {response.content}")
            
        return None
        
    except Exception as e:
        print(f"[Soft Check] 软性判断出错: {e}")
        return None

