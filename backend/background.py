# background.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, Any
import os
from dotenv import load_dotenv

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain.output_parsers import PydanticOutputParser

# 加载环境变量，例如 OPENAI_API_KEY
load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")

if not openai_api_key:
    raise ValueError("OPENAI_API_KEY is not set in environment variables.")

# 关键改动: 使用 APIRouter() 而不是 FastAPI()
background_router = APIRouter()

# 关键修复: 在这里定义 PromptRequest 类，使其对当前文件可见
class PromptRequest(BaseModel):
    prompt: str

# --- 1. 使用 Pydantic v2 的 BaseModel ---
class CharacterDescription(BaseModel):
    description: str = Field(description="一个完整的克苏鲁人物描述")

# --- 2. 创建 LangChain 逻辑 ---
async def generate_character_description_with_langchain(prompt: str) -> Dict[str, str]:
    """
    使用 LangChain 根据提供的提示生成并解析人物描述。
    """
    try:
        base_system_prompt = """
        你是一个帮助跑团玩家创建角色描述的助手。请根据以下角色信息生成一个完整的人物描述，用于克苏鲁的呼唤跑团游戏。要求：
        1. 内容分为若干段落，包括角色的背景、性格、特质、技能等，只突出关键细节。
        2. 风格沉浸、有理有据，符合克苏鲁和爱手艺大师的风格，可以适当发挥创意，但不得过于脱离角色已有信息。
        3. 不要出现具体的属性分数，仅重点描述属性的几项特长和弱点，不要覆盖太多属性。
        4. 请基于 keylink 推断一段与其强相关的个人经历或情感纽带。
        5. 请严格返回下面的 JSON 格式，不要包含任何额外文本。
        """
        
        parser = PydanticOutputParser(pydantic_object=CharacterDescription)

        prompt_template = ChatPromptTemplate.from_messages([
            ("system", base_system_prompt + "\n\n{format_instructions}"),
            ("user", "{user_input}"),
        ])

        formatted_prompt = prompt_template.format_messages(
            format_instructions=parser.get_format_instructions(),
            user_input=prompt,
        )

        llm = ChatOpenAI(
            api_key=openai_api_key,
            model="gpt-4o-mini",
            temperature=0.7,
        )

        llm_response = await llm.ainvoke(formatted_prompt)
        print("LLM raw response content:", llm_response.content)

        parsed_output = parser.parse(llm_response.content)
        
        return parsed_output.dict()

    except Exception as e:
        print(f"Error in generate_character_description_with_langchain: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@background_router.post("/generate_description")
async def handle_generate_description(request: PromptRequest):
    print("Received prompt for character description:", request.prompt)
    try:
        description_data = await generate_character_description_with_langchain(request.prompt)
        return description_data
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Internal server error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error.")
