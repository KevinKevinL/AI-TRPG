# memory_manager.py

import chromadb
import json
import os
import redis
from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid

class ChromaMemoryManager:
    def __init__(self, persist_directory: str = None, redis_client: redis.Redis = None):
        if persist_directory is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            persist_directory = os.path.join(current_dir, "..", "chroma_db")
        
        # 确保目录存在
        os.makedirs(persist_directory, exist_ok=True)
        
        # 初始化ChromaDB客户端
        self.client = chromadb.PersistentClient(path=persist_directory)
        
        # 创建或获取NPC记忆集合
        self.npc_memories = self.client.get_or_create_collection(
            name="npc_memories",
            metadata={"description": "NPC长期记忆存储"}
        )
        
        # 初始化Redis客户端
        self.redis_client = redis_client or redis.Redis(host='localhost', port=6379, db=0)
        
        print(f"ChromaDB记忆管理器初始化完成，数据目录: {persist_directory}")
        print("Redis短期记忆管理已启用")
    
    def add_npc_memory(self, 
                       character_id: str, 
                       memory_text: str, 
                       context: Dict[str, Any] = None) -> str:
        """
        添加NPC记忆
        
        Args:
            character_id: NPC的ID
            memory_text: 记忆内容（简洁的当前观察/反应）
            context: 额外的上下文信息
        
        Returns:
            memory_id: 生成的记忆ID
        """
        memory_id = str(uuid.uuid4())
        
        print(f"为NPC {character_id} 添加了新记忆: {memory_text[:50]}...")
        
        # 只添加到Redis短期记忆，不直接添加到ChromaDB
        # 只有当短期记忆达到20条时，才会压缩到ChromaDB
        self._add_to_short_term_memory(character_id, memory_text, context)
        
        return memory_id
    
    def get_npc_memories(self, 
                         character_id: str, 
                         limit: int = 5,
                         query_text: str = None) -> List[Dict[str, Any]]:
        """
        获取NPC的长期记忆（用于直接查询）
        
        Args:
            character_id: NPC的ID
            limit: 返回的记忆数量
            query_text: 可选的查询文本，用于语义搜索
        
        Returns:
            记忆列表
        """
        if query_text:
            # 语义搜索
            results = self.npc_memories.query(
                query_texts=[query_text],
                n_results=limit,
                where={"character_id": character_id}
            )
        else:
            # 获取最近的记忆
            results = self.npc_memories.get(
                where={"character_id": character_id},
                limit=limit
            )
        
        memories = []
        if results and 'metadatas' in results:
            for i, metadata in enumerate(results['metadatas']):
                memory = {
                    "memory_id": results['ids'][i] if 'ids' in results else str(i),
                    "content": results['documents'][i] if 'documents' in results else "",
                    "timestamp": metadata.get("timestamp", ""),
                    "context": json.loads(metadata.get("context", "{}"))
                }
                memories.append(memory)
        
        return memories
    
    def _add_to_short_term_memory(self, character_id: str, memory_text: str, context: Dict[str, Any]):
        """添加记忆到Redis短期记忆"""
        try:
            memory_data = {
                "timestamp": datetime.now().isoformat(),
                "content": memory_text,
                "context": context
            }
            
            # 使用LPUSH添加到短期记忆列表左侧（最新）
            # 设置ensure_ascii=False，确保中文字符正常显示
            redis_key = f"short_term_memory:{character_id}"
            self.redis_client.lpush(redis_key, json.dumps(memory_data, ensure_ascii=False))
            
            # 检查是否需要压缩记忆
            self._check_and_compress_memories(character_id)
            
        except Exception as e:
            print(f"添加短期记忆失败: {e}")
    
    def _check_and_compress_memories(self, character_id: str):
        """检查并压缩短期记忆"""
        try:
            redis_key = f"short_term_memory:{character_id}"
            memory_count = self.redis_client.llen(redis_key)
            
            if memory_count >= 20:
                print(f"NPC {character_id} 短期记忆达到 {memory_count} 条，开始压缩...")
                self._compress_old_memories(character_id)
            else:
                print(f"NPC {character_id} 短期记忆数量: {memory_count}/20")
                
        except Exception as e:
            print(f"检查记忆压缩失败: {e}")
    
    def _compress_old_memories(self, character_id: str):
        """压缩最旧的10条记忆为长期记忆"""
        try:
            redis_key = f"short_term_memory:{character_id}"
            
            # 提取最旧的10条记忆（列表右侧）
            old_memories = self.redis_client.lrange(redis_key, -10, -1)
            
            if not old_memories:
                return
            
            # 解析记忆数据
            memory_texts = []
            for memory_json in old_memories:
                try:
                    memory_data = json.loads(memory_json)
                    memory_texts.append(memory_data.get('content', ''))
                except:
                    continue
            
            if not memory_texts:
                return
            
            # 拼接记忆文本
            combined_text = "\n".join(memory_texts)
            
            # 使用LLM压缩记忆（这里需要异步调用）
            compressed_memory = self._compress_with_llm(combined_text, character_id)
            
            if compressed_memory:
                # 添加到ChromaDB长期记忆
                compression_context = {
                    "source": "compression", 
                    "original_count": len(memory_texts),
                    "compression_type": "automatic"
                }
                
                self.npc_memories.add(
                    documents=[compressed_memory],
                    metadatas=[{
                        "character_id": character_id,
                        "timestamp": datetime.now().isoformat(),
                        "context": json.dumps(compression_context, ensure_ascii=False)
                    }],
                    ids=[f"compressed_{character_id}_{datetime.now().timestamp()}"]
                )
                
                # 删除已压缩的旧记忆，保留最新的10条
                self.redis_client.ltrim(redis_key, 0, 9)
                
                print(f"NPC {character_id} 的记忆压缩完成，生成了1条长期记忆")
                
        except Exception as e:
            print(f"压缩记忆失败: {e}")
    

    
    def _compress_with_llm(self, memory_texts: str, character_id: str) -> str:
        """使用LLM压缩记忆文本为长期记忆"""
        try:
            from langchain_openai import ChatOpenAI
            from langchain_core.messages import SystemMessage, HumanMessage
            
            llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.1)
            
            system_prompt = f"""
                你是一个记忆压缩专家。你的任务是将NPC {character_id} 的多个短期记忆压缩成一条简洁的长期记忆。

                压缩要求：
                1. 保留关键信息和情感
                2. 去除重复内容
                3. 用简洁的语言概括
                4. 保持记忆的连贯性
                5. 长度控制在100-200字以内
                
                请直接返回压缩后的记忆内容，不要添加任何解释或格式。"""

            human_prompt = f"请压缩以下记忆：\n\n{memory_texts}"
            
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=human_prompt)
            ]
            
            response = llm.invoke(messages)
            compressed_memory = response.content.strip()
            
            print(f"LLM记忆压缩完成，原文长度: {len(memory_texts)}，压缩后长度: {len(compressed_memory)}")
            return compressed_memory
            
        except Exception as e:
            print(f"LLM记忆压缩失败: {e}")
            # 如果LLM失败，回退到简单压缩
            fallback = f"NPC {character_id} 的长期记忆摘要：{memory_texts[:200]}..."
            print(f"使用回退压缩: {fallback[:100]}...")
            return fallback
    
    def get_npc_memories_for_context(self, character_id: str, limit: int = 5) -> Dict[str, Any]:
        """获取NPC的短期记忆和长期记忆，用于NPC Loop"""
        try:
            # 获取短期记忆（Redis）
            redis_key = f"short_term_memory:{character_id}"
            short_term_memories = []
            
            # 获取最近的短期记忆（最多10条）
            short_term_data = self.redis_client.lrange(redis_key, 0, 9)
            for memory_json in short_term_data:
                try:
                    memory_data = json.loads(memory_json)
                    short_term_memories.append({
                        "content": memory_data.get('content', ''),
                        "timestamp": memory_data.get('timestamp', '')
                    })
                except:
                    continue
            
            # 获取长期记忆（ChromaDB，基于相似度搜索）
            long_term_memories = []
            if short_term_memories:
                # 使用最新的短期记忆作为查询文本
                latest_memory = short_term_memories[0]['content']
                long_term_results = self.npc_memories.query(
                    query_texts=[latest_memory],
                    n_results=3,
                    where={"character_id": character_id}
                )
                
                if long_term_results and 'metadatas' in long_term_results:
                    for i, metadata in enumerate(long_term_results['metadatas'][0]):
                        long_term_memories.append({
                            "content": long_term_results['documents'][0][i],
                            "timestamp": metadata.get('timestamp', ''),
                            "similarity": long_term_results['distances'][0][i] if 'distances' in long_term_results else 0
                        })
            
            return {
                "short_term": short_term_memories,
                "long_term": long_term_memories,
                "total_short_term": len(short_term_memories),
                "total_long_term": len(long_term_memories)
            }
            
        except Exception as e:
            print(f"获取NPC记忆上下文失败: {e}")
            return {"short_term": [], "long_term": [], "total_short_term": 0, "total_long_term": 0}
    

    


# 创建全局实例
# 注意：这里需要传入Redis客户端，或者确保Redis连接可用
try:
    from redis_manager import redis_client
    memory_manager = ChromaMemoryManager(redis_client=redis_client)
except ImportError:
    print("警告：无法导入redis_client，使用默认Redis连接")
    memory_manager = ChromaMemoryManager()
