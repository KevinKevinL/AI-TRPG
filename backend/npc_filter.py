#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NPC筛选器：智能筛选需要反应的NPC
"""

from typing import List, Dict, Any, Optional
import json
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

class NPCFilter:
    def __init__(self):
        self.llm = None
    
    def _get_llm(self):
        """延迟初始化LLM"""
        if self.llm is None:
            try:
                self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.1)
                print("[NPC筛选器] LLM初始化成功")
            except Exception as e:
                print(f"[NPC筛选器] LLM初始化失败: {e}")
                return None
        return self.llm
    
    async def filter_npcs_by_relevance(
        self, 
        player_input: str, 
        player_action: Dict[str, Any], 
        available_npcs: List[Dict[str, Any]], 
        max_npcs: int = 3,
        recent_npcs: List[str] = None
    ) -> List[Dict[str, Any]]:
        """
        根据玩家行动的相关性筛选NPC，增加多样性和轮换机制
        
        Args:
            player_input: 玩家输入文本
            player_action: 解析后的玩家行动
            available_npcs: 可用的NPC列表
            max_npcs: 最大激活NPC数量
            recent_npcs: 最近几轮已经激活的NPC ID列表
            
        Returns:
            筛选后的NPC列表
        """
        if not available_npcs:
            return []
        
        if len(available_npcs) <= max_npcs:
            return available_npcs
        
        # 使用LLM筛选，考虑多样性
        return await self._llm_filter_npcs(player_input, player_action, available_npcs, max_npcs, recent_npcs)
    
    async def _llm_filter_npcs(
        self, 
        player_input: str, 
        player_action: Dict[str, Any], 
        available_npcs: List[Dict[str, Any]], 
        max_npcs: int,
        recent_npcs: List[str] = None
    ) -> List[Dict[str, Any]]:
        """使用LLM智能筛选NPC，考虑多样性"""
        
        # 构建NPC信息
        npc_info_list = []
        for npc in available_npcs:
            npc_info = {
                "id": npc.get('id', ''),
                "name": npc.get('name', ''),
                "profession": npc.get('profession', ''),
                "status": npc.get('status', ''),
                "current_goal": npc.get('current_goal', ''),
                "initial_knowledge": npc.get('initial_knowledge', ''),
                "roleplay_guidelines": npc.get('roleplay_guidelines', '')
            }
            npc_info_list.append(npc_info)
        
        # 构建最近激活NPC信息
        recent_info = ""
        if recent_npcs:
            recent_info = f"\n最近几轮已激活的NPC: {recent_npcs}\n"
        
        system_prompt = f"""
        你是一个COC跑团的NPC筛选器。根据玩家的行动和当前情况，从可用NPC中选择最相关的NPC来做出反应。

        玩家输入: {player_input}
        玩家行动: {json.dumps(player_action, ensure_ascii=False)}
        
        可用NPC列表:
        {json.dumps(npc_info_list, ensure_ascii=False, indent=2)}
        {recent_info}
        
        筛选标准（按优先级排序）:
        1. **明确指定对象**: 如果玩家明确指定要与某个NPC交谈，只激活该NPC
        2. **直接相关性**: NPC是否与玩家行动直接相关（如：玩家询问信息，NPC知道相关内容）
        3. **位置相关性**: NPC是否在玩家行动发生的位置附近
        4. **状态相关性**: NPC当前状态是否允许或需要做出反应
        5. **剧情相关性**: NPC是否与当前剧情发展相关
        6. **多样性考虑**: 优先选择最近几轮没有激活的NPC，增加剧情多样性
        7. **角色重要性**: 重要NPC优先考虑
        
        【重要】筛选原则：
        - 如果玩家明确指定交谈对象（如"问杰克"、"和玛丽说话"），只激活该NPC（1个）
        - 如果玩家行动是面向所有人的（如"大家听我说"），则选择多个相关NPC（最多{max_npcs}个）
        - 如果玩家行动是观察或检查，选择最相关的1-2个NPC
        - 如果最近几轮总是同样的NPC，优先选择其他NPC增加多样性
        - 给所有NPC公平的参与机会
        
        请返回JSON格式的筛选结果，包含选中的NPC ID列表和选择理由:
        {{
            "selected_npc_ids": ["npc_id1", "npc_id2", ...],
            "reasoning": "选择理由说明，包括为什么选择这个数量的NPC"
        }}
        
        严格只返回JSON格式，不要其他内容。
        """
        
        try:
            llm = self._get_llm()
            if not llm:
                print("[NPC筛选器] LLM不可用，返回所有NPC")
                return available_npcs
            
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content="请筛选最相关的NPC")
            ]
            
            response = await llm.ainvoke(messages)
            result = json.loads(response.content)
            
            # 根据筛选结果返回NPC
            selected_ids = result.get('selected_npc_ids', [])
            selected_npcs = [npc for npc in available_npcs if npc.get('id') in selected_ids]
            
            print(f"[NPC筛选器] 从{len(available_npcs)}个NPC中筛选出{len(selected_npcs)}个")
            print(f"[NPC筛选器] 选择理由: {result.get('reasoning', '无')}")
            
            return selected_npcs
            
        except Exception as e:
            print(f"[NPC筛选器] LLM筛选失败: {e}，返回所有NPC")
            return available_npcs
    


# 创建全局实例
npc_filter = NPCFilter()
