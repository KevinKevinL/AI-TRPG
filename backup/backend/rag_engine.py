import os
import pandas as pd
import tiktoken
from dotenv import load_dotenv

from graphrag.query.context_builder.entity_extraction import EntityVectorStoreKey
from graphrag.query.indexer_adapters import (
    read_indexer_covariates,
    read_indexer_entities,
    read_indexer_relationships,
    read_indexer_reports,
    read_indexer_text_units,
)
from graphrag.query.structured_search.local_search.mixed_context import LocalSearchMixedContext
from graphrag.query.structured_search.local_search.search import LocalSearch
from graphrag.vector_stores.lancedb import LanceDBVectorStore
from graphrag.config.enums import ModelType
from graphrag.config.models.language_model_config import LanguageModelConfig
from graphrag.language_model.manager import ModelManager

# 加载环境变量
load_dotenv()

class RAGEngine:
    def __init__(self, base_dir: str):
        # 打印正在使用的路径，以确认是否正确
        print(f"尝试初始化 GraphRAG 引擎，基准目录: {base_dir}")
        self.search_engine = self.initialize_graphrag_search_engine(base_dir)

    def initialize_graphrag_search_engine(self, base_dir: str):
        """
        初始化并返回一个 GraphRAG LocalSearch 实例。
        """
        try:
            inputs_dir = base_dir
            lancedb_uri = os.path.join(base_dir, "lancedb")

            print("--- GraphRAG 初始化步骤 ---")
            print(f"检查目录: {inputs_dir}")
            if not os.path.exists(inputs_dir):
                print(f"错误: GraphRAG 目录 '{inputs_dir}' 不存在。")
                return None
            
            print(f"检查 LanceDB 路径: {lancedb_uri}")
            if not os.path.exists(lancedb_uri):
                print(f"错误: LanceDB 目录 '{lancedb_uri}' 不存在。")
                return None

            print("检查环境变量...")
            api_key = os.getenv("GRAPHRAG_API_KEY")
            llm_model = os.getenv("GRAPHRAG_LLM_MODEL", "gpt-4o-mini")
            embedding_model = os.getenv("GRAPHRAG_EMBEDDING_MODEL", "text-embedding-3-small")

            if not api_key:
                print("错误: 环境变量 GRAPHRAG_API_KEY 未设置。")
                return None
            
            print(f"LLM 模型: {llm_model}")
            print(f"Embedding 模型: {embedding_model}")

            print("读取 Parquet 文件...")
            entity_df = pd.read_parquet(f"{inputs_dir}/entities.parquet")
            community_df = pd.read_parquet(f"{inputs_dir}/communities.parquet")
            relationship_df = pd.read_parquet(f"{inputs_dir}/relationships.parquet")
            report_df = pd.read_parquet(f"{inputs_dir}/community_reports.parquet")
            text_unit_df = pd.read_parquet(f"{inputs_dir}/text_units.parquet")

            print("检查 covariates.parquet...")
            covariates_path = f"{inputs_dir}/covariates.parquet"
            if os.path.exists(covariates_path):
                covariate_df = pd.read_parquet(covariates_path)
                claims = read_indexer_covariates(covariate_df)
                covariates = {"claims": claims}
                print("已成功加载 covariates.parquet。")
            else:
                print("未找到 covariates.parquet 文件，将跳过协变量加载。")
                covariates = None

            print("转换为 GraphRAG 数据对象...")
            entities = read_indexer_entities(entity_df, community_df, 2)
            relationships = read_indexer_relationships(relationship_df)
            reports = read_indexer_reports(report_df, community_df, 2)
            text_units = read_indexer_text_units(text_unit_df)

            print("初始化 LLM 模型...")
            chat_config = LanguageModelConfig(
                api_key=api_key,
                type=ModelType.OpenAIChat,
                model=llm_model,
                max_retries=20,
            )
            chat_model = ModelManager().get_or_create_chat_model(
                name="local_search",
                model_type=ModelType.OpenAIChat,
                config=chat_config,
            )
            token_encoder = tiktoken.encoding_for_model(llm_model)

            embedding_config = LanguageModelConfig(
                api_key=api_key,
                type=ModelType.OpenAIEmbedding,
                model=embedding_model,
                max_retries=20,
            )
            text_embedder = ModelManager().get_or_create_embedding_model(
                name="local_search_embedding",
                model_type=ModelType.OpenAIEmbedding,
                config=embedding_config,
            )

            print("初始化 LanceDB...")
            description_embedding_store = LanceDBVectorStore(collection_name="default-entity-description")
            description_embedding_store.connect(db_uri=lancedb_uri)
            print("LanceDB 连接成功。")

            print("创建上下文构建器和搜索引擎...")
            context_builder = LocalSearchMixedContext(
                community_reports=reports,
                text_units=text_units,
                entities=entities,
                relationships=relationships,
                covariates=covariates,
                entity_text_embeddings=description_embedding_store,
                embedding_vectorstore_key=EntityVectorStoreKey.ID,
                text_embedder=text_embedder,
                token_encoder=token_encoder,
            )

            local_context_params = {
                "text_unit_prop": 0.5,
                "community_prop": 0.1,
                "conversation_history_max_turns": 5,
                "conversation_history_user_turns_only": True,
                "top_k_mapped_entities": 10,
                "top_k_relationships": 10,
                "include_entity_rank": True,
                "include_relationship_weight": True,
                "include_community_rank": False,
                "return_candidate_context": False,
                "embedding_vectorstore_key": EntityVectorStoreKey.ID,
                "max_tokens": 12_000,
            }
            model_params = {
                "max_tokens": 2_000,
                "temperature": 0.0,
            }

            search_engine = LocalSearch(
                model=chat_model,
                context_builder=context_builder,
                token_encoder=token_encoder,
                model_params=model_params,
                context_builder_params=local_context_params,
                response_type="multiple paragraphs",
            )
            print("--- GraphRAG 初始化完成 ---")
            return search_engine

        except Exception as e:
            # 捕获异常并打印完整的 traceback
            import traceback
            print("\n" + "="*50)
            print("!!! GraphRAG 初始化失败 !!!")
            print(f"错误信息: {e}")
            print("--- 详细追踪 ---")
            traceback.print_exc()
            print("="*50 + "\n")
            return None

# 在模块加载时创建 RAGEngine 实例
current_dir = os.path.dirname(os.path.abspath(__file__))
rag_dir = os.path.join(current_dir, "rag", "output")
rag_engine = RAGEngine(rag_dir)