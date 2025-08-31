# chroma_interactive.py
# 交互式ChromaDB查看工具

import chromadb
import json
import os

def chroma_interactive():
    print("=== ChromaDB 交互式查看器 ===")
    print("输入 'help' 查看可用命令")
    print("输入 'quit' 退出\n")
    
    # 连接到ChromaDB
    current_dir = os.path.dirname(os.path.abspath(__file__))
    chroma_path = os.path.join(current_dir, "..", "chroma_db")
    
    client = chromadb.PersistentClient(path=chroma_path)
    collection = client.get_collection("npc_memories")
    
    while True:
        try:
            command = input("ChromaDB> ").strip().lower()
            
            if command == 'quit' or command == 'exit':
                break
            elif command == 'help':
                print("可用命令:")
                print("  count - 查看总文档数量")
                print("  list - 列出所有文档")
                print("  search <query> - 语义搜索")
                print("  npc <npc_id> - 查看特定NPC的记忆")
                print("  stats - 查看统计信息")
                print("  delete - 显示删除选项")
                print("  delete all - 删除所有记忆")
                print("  delete npc <npc_id> - 删除特定NPC的所有记忆")
                print("  delete id <memory_id> - 删除特定记忆")
                print("  short <npc_id> - 查看特定NPC的短期记忆")
                print("  quit - 退出")
            elif command == 'count':
                count = collection.count()
                print(f"总文档数量: {count}")
            elif command == 'list':
                results = collection.get()
                if results and results['metadatas']:
                    print(f"找到 {len(results['metadatas'])} 个文档:")
                    for i, (doc_id, metadata, document) in enumerate(zip(results['ids'], results['metadatas'], results['documents'])):
                        print(f"  {i+1}. ID: {doc_id}")
                        print(f"     NPC: {metadata.get('character_id', 'N/A')}")
                        print(f"     内容: {document[:100]}...")
                        print()
                else:
                    print("没有找到文档")
            elif command.startswith('search '):
                query = command[7:].strip()
                if query:
                    results = collection.query(query_texts=[query], n_results=5)
                    if results and results['metadatas']:
                        print(f"搜索 '{query}' 的结果:")
                        for i, (doc_id, metadata, document, distance) in enumerate(zip(
                            results['ids'][0], results['metadatas'][0], 
                            results['documents'][0], results['distances'][0]
                        )):
                            print(f"  {i+1}. 距离: {distance:.3f}")
                            print(f"     NPC: {metadata.get('character_id', 'N/A')}")
                            print(f"     内容: {document}")
                            print()
                    else:
                        print("没有找到相关结果")
                else:
                    print("请输入搜索查询")
            elif command.startswith('npc '):
                npc_id = command[4:].strip()
                if npc_id:
                    results = collection.get(where={"character_id": npc_id})
                    if results and results['metadatas']:
                        print(f"NPC {npc_id} 的记忆:")
                        for i, (doc_id, metadata, document) in enumerate(zip(results['ids'], results['metadatas'], results['documents'])):
                            print(f"  {i+1}. {document}")
                            print(f"     时间: {metadata.get('timestamp', 'N/A')}")
                            print()
                    else:
                        print(f"NPC {npc_id} 没有记忆")
                else:
                    print("请输入NPC ID")
            elif command == 'stats':
                results = collection.get()
                if results and results['metadatas']:
                    npc_stats = {}
                    type_stats = {}
                    total_importance = 0
                    
                    for metadata in results['metadatas']:
                        npc_id = metadata.get("character_id", "unknown")
                        npc_stats[npc_id] = npc_stats.get(npc_id, 0) + 1
                    
                    print("统计信息:")
                    print(f"  总文档数: {len(results['metadatas'])}")
                    print(f"  NPC数量: {len(npc_stats)}")
                    print("  NPC分布:")
                    for npc_id, count in npc_stats.items():
                        print(f"    {npc_id}: {count} 条记忆")
                else:
                    print("没有数据可统计")
            elif command == 'delete':
                print("删除选项:")
                print("  delete all - 删除所有记忆")
                print("  delete npc <npc_id> - 删除特定NPC的所有记忆")
                print("  delete id <memory_id> - 删除特定记忆")
            elif command == 'delete all':
                confirm = input("确定要删除所有记忆吗？(输入 'yes' 确认): ")
                if confirm.lower() == 'yes':
                    # 先获取所有文档的ID，然后删除
                    all_results = collection.get()
                    if all_results and all_results['ids']:
                        collection.delete(ids=all_results['ids'])
                        print("所有记忆已删除")
                    else:
                        print("没有找到需要删除的记忆")
                else:
                    print("删除操作已取消")
            elif command.startswith('delete npc '):
                npc_id = command[11:].strip()
                if npc_id:
                    confirm = input(f"确定要删除NPC {npc_id} 的所有记忆吗？(输入 'yes' 确认): ")
                    if confirm.lower() == 'yes':
                        collection.delete(where={"character_id": npc_id})
                        print(f"NPC {npc_id} 的所有记忆已删除")
                    else:
                        print("删除操作已取消")
                else:
                    print("请输入NPC ID")
            elif command.startswith('delete id '):
                memory_id = command[10:].strip()
                if memory_id:
                    confirm = input(f"确定要删除记忆 {memory_id} 吗？(输入 'yes' 确认): ")
                    if confirm.lower() == 'yes':
                        collection.delete(ids=[memory_id])
                        print(f"记忆 {memory_id} 已删除")
                    else:
                        print("删除操作已取消")
                else:
                    print("请输入记忆ID")

            elif command.startswith('short '):
                npc_id = command[6:].strip()
                if npc_id:
                    try:
                        from memory_manager import memory_manager
                        memory_data = memory_manager.get_npc_memories_for_context(npc_id)
                        
                        print(f"NPC {npc_id} 的记忆状态:")
                        print(f"  短期记忆: {memory_data['total_short_term']} 条")
                        print(f"  长期记忆: {memory_data['total_long_term']} 条")
                        
                        if memory_data['short_term']:
                            print("\n【短期记忆】")
                            for i, memory in enumerate(memory_data['short_term'], 1):
                                print(f"  {i}. {memory['content'][:100]}...")
                                print(f"     时间: {memory['timestamp']}")
                        
                        if memory_data['long_term']:
                            print("\n【长期记忆】")
                            for i, memory in enumerate(memory_data['long_term'], 1):
                                print(f"  {i}. {memory['content'][:100]}...")
                                print(f"     相似度: {1-memory.get('similarity', 0):.2f}")
                        
                    except Exception as e:
                        print(f"查看短期记忆失败: {e}")
                else:
                    print("请输入NPC ID")
            else:
                print("未知命令，输入 'help' 查看可用命令")
                
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"错误: {e}")
    
    print("再见！")

if __name__ == "__main__":
    chroma_interactive()
