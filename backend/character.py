# character.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from character_state import set_current_character_id

# 创建角色路由器
character_router = APIRouter()

# 定义角色ID请求模型
class CharacterIdRequest(BaseModel):
    character_id: str

@character_router.post("/character_entered")
async def handle_character_entered(request: CharacterIdRequest):
    """
    当用户进入游戏页面时，接收当前角色ID
    """
    try:
        character_id = request.character_id
        print(f"用户进入游戏页面，当前角色ID: {character_id}")
        
        # 更新共享的角色状态
        set_current_character_id(character_id)
        
        # 这里以后可以把角色数据加载到redis
        
        return {
            "status": "success",
            "message": f"角色ID {character_id} 已接收",
            "character_id": character_id
        }
    except Exception as e:
        print(f"处理角色进入时出错: {e}")
        raise HTTPException(status_code=500, detail="处理角色进入时出错")
