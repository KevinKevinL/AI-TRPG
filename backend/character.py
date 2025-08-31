# character.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from character_state import set_current_character_id
from databaseManager import db_manager
from redis_manager import (
    save_character_sheet, 
    save_session_state, 
    get_session_state, 
    get_character_sheet,
    save_map_state # 导入新函数
)
import json

character_router = APIRouter()

class CharacterIdRequest(BaseModel):
    character_id: str

@character_router.post("/character_entered")
async def handle_character_entered(request: CharacterIdRequest):
    """
    当用户进入游戏时, 加载玩家、NPC和地图物品数据到Redis
    """
    try:
        character_id = request.character_id
        set_current_character_id(character_id)
        
        # 0. 先更新数据库中的位置和载具信息
        update_query = "UPDATE characters SET current_location_id = ?, current_vehicle_id = ? WHERE id = ?"
        db_manager.execute_query(update_query, (1, 101, character_id))
        print(f"已更新角色 {character_id} 的数据库字段：current_location_id=1, current_vehicle_id=101")
        
        # 1. 加载玩家静态数据 (Character Sheet)
        sheet_data = db_manager.get_character_data(character_id)
        if not sheet_data or not sheet_data.get('info'):
            raise HTTPException(status_code=404, detail="角色不存在")
        
        # 2. 构建玩家初始动态状态 (Session State)
        derived_attrs = sheet_data.get('derived_attributes', {})
        current_map_id = sheet_data.get('info', {}).get('current_location_id', 1)
        print(f"将为角色 {character_id} 加载地图 {current_map_id} 的动态实体")
        session_state = {
            "hp": derived_attrs.get("hit_points", 0),
            "sanity": derived_attrs.get("sanity", 0),
            "mp": derived_attrs.get("magic_points", 0),
            "current_map_id": current_map_id,
            "current_vehicle_id": sheet_data.get('info', {}).get('current_vehicle_id', 101),
            "pending_check_event_id": None
        }
        
        # 3. 加载当前地图的动态实体 (Map State)
        npcs_on_map = db_manager.get_npcs_on_map(current_map_id)
        objects_on_map = db_manager.get_objects_on_map(current_map_id)
        print(f"地图 {current_map_id} 查询结果：NPC数量={len(npcs_on_map)}, 物品数量={len(objects_on_map)}")
        
        map_state = {
            "npcs": [npc['id'] for npc in npcs_on_map],
            "objects": {str(obj['object_id']): obj['current_state'] for obj in objects_on_map}
        }
        
        # 4. 将所有数据分别存入Redis
        save_character_sheet(character_id, sheet_data)
        print(f"已保存角色卡到Redis: {character_id}")
        save_session_state(character_id, session_state)
        print(f"已保存会话状态到Redis: {session_state}")
        save_map_state(current_map_id, map_state)
        print(f"已保存地图状态到Redis: map_id={current_map_id}, map_state={map_state}")
        
        # 为地图上的每个NPC也创建初始session_state (如果不存在)
        for npc in npcs_on_map:
            npc_id = npc['id']
            print(f"处理地图NPC: {npc_id}")
            
            # 确保NPC的完整数据保存到Redis
            npc_sheet = db_manager.get_character_data(npc_id)
            if npc_sheet:
                print(f"保存NPC {npc_id} 的完整数据到Redis")
                save_character_sheet(npc_id, npc_sheet)
                
                # 创建或更新NPC的session_state
                if not get_session_state(npc_id):
                    npc_derived = npc_sheet.get('derived_attributes', {})
                    npc_session = {
                        "hp": npc_derived.get("hit_points", 10),
                        "sanity": npc_derived.get("sanity", 50),
                        "mp": npc_derived.get("magic_points", 10),
                        "current_map_id": npc_sheet.get('info', {}).get('current_location_id', current_map_id),
                        "current_vehicle_id": npc_sheet.get('info', {}).get('current_vehicle_id', None),
                    }
                    save_session_state(npc_id, npc_session)
                    print(f"为NPC {npc_id} 创建了新的session_state")
                else:
                    print(f"NPC {npc_id} 已有session_state，跳过创建")
            else:
                print(f"警告：无法获取NPC {npc_id} 的完整数据")

        print(f"角色 {character_id} 和地图 {current_map_id} 的所有动态状态已加载到Redis")
        
        return {"status": "success", "message": "所有状态已成功加载到Redis", "map_state_counts": {"npcs": len(npcs_on_map), "objects": len(objects_on_map)}}
        
    except Exception as e:
        import traceback
        print(f"处理角色进入时出错: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"处理角色进入时出错: {e}")

@character_router.get("/character_sheet/{character_id}")
async def api_get_character_sheet(character_id: str):
    return get_character_sheet(character_id)

@character_router.get("/session_state/{character_id}")
async def api_get_session_state(character_id: str):
    return get_session_state(character_id)

@character_router.get("/character_data")
async def api_get_character_data(character_id: str):
    """
    获取完整的角色数据，包括静态数据（角色卡）和动态状态
    这个接口用于前端显示角色信息
    """
    try:
        # 1. 获取角色静态数据（角色卡）
        character_sheet = get_character_sheet(character_id)
        if not character_sheet:
            raise HTTPException(status_code=404, detail="角色不存在")
        
        # 2. 获取角色动态状态
        session_state = get_session_state(character_id)
        if not session_state:
            # 如果没有session_state，创建一个默认的
            derived_attrs = character_sheet.get('derived_attributes', {})
            session_state = {
                "hp": derived_attrs.get("hit_points", 0),
                "sanity": derived_attrs.get("sanity", 0),
                "mp": derived_attrs.get("magic_points", 0),
                "current_map_id": character_sheet.get('info', {}).get('current_location_id', 1),
                "current_vehicle_id": character_sheet.get('info', {}).get('current_vehicle_id', None),
            }
            save_session_state(character_id, session_state)
        
        # 3. 构建返回数据结构，适配前端需求
        response_data = {
            "info": character_sheet.get('info', {}),
            "attributes": character_sheet.get('attributes', {}),
            "derived_attributes": character_sheet.get('derived_attributes', {}),
            "skills": character_sheet.get('skills', {}),
            "backgrounds": character_sheet.get('backgrounds', {}),
            "status": {
                "hit_points": session_state.get("hp", 0),
                "magic_points": session_state.get("mp", 0),
                "sanity": session_state.get("sanity", 0),
                "current_map_id": session_state.get("current_map_id", 1),
                "current_vehicle_id": session_state.get("current_vehicle_id", None),
            }
        }
        
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"获取角色数据时出错: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"获取角色数据时出错: {e}")
