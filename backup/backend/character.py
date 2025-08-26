# character.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from character_state import set_current_character_id
from databaseManager import db_manager
from redis_manager import save_character_data_to_redis
import json

character_router = APIRouter()

class CharacterIdRequest(BaseModel):
    character_id: str

@character_router.post("/character_entered")
async def handle_character_entered(request: CharacterIdRequest):
    """
    当用户进入游戏页面时，接收当前角色ID并加载角色数据到Redis
    """
    try:
        character_id = request.character_id
        print(f"用户进入游戏页面，当前角色ID: {character_id}")
        
        # 更新共享的角色状态
        set_current_character_id(character_id)
        
        # 从数据库获取角色数据
        character_info = db_manager.get_character_info(character_id)
        character_attributes = db_manager.get_character_attributes(character_id)
        character_skills = db_manager.get_character_skills(character_id)
        character_derived_attributes = db_manager.get_character_derived_attributes(character_id)
        
        if not character_info:
            raise HTTPException(status_code=404, detail="角色不存在")
        
        # 构建完整的角色数据
        character_data = {
            "info": character_info,
            "attributes": character_attributes,
            "skills": character_skills,
            "derived_attributes": character_derived_attributes
        }
        
        # 构建角色状态数据
        character_status = {
            "current_location": "起始位置",  # 默认起始位置
            "current_map_id": "1",  # 默认地图ID
            "sanity": character_derived_attributes.get("sanity", 99),
            "health": character_derived_attributes.get("hitPoints", 10),
            "magic": character_derived_attributes.get("magicPoints", 10)
        }
        
        # 使用新的Redis管理函数保存数据
        save_success = save_character_data_to_redis(character_id, character_data, character_status)
        
        if save_success:
            print(f"角色 {character_id} 的数据已成功加载到Redis")
        else:
            print(f"角色 {character_id} 的数据保存到Redis失败，但不影响角色进入游戏")
        
        return {
            "status": "success",
            "message": f"角色ID {character_id} 已接收，数据已加载",
            "character_id": character_id,
            "character_data": character_data,
            "character_status": character_status
        }
        
    except Exception as e:
        print(f"处理角色进入时出错: {e}")
        raise HTTPException(status_code=500, detail="处理角色进入时出错")
