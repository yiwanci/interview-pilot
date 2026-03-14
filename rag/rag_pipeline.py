"""
RAG 完整流程
入库 + 检索 + 生成
"""
from typing import Optional
from openai import OpenAI

from config import get_llm_config
from storage import RawDocument, DocumentChunk, VectorStore
from .chunker import AdaptiveChunker
from .embedder import Embedder
from .retriever import HybridRetriever
from .reranker import get_reranker, BaseReranker


class RAGPipeline:
    """
    RAG 完整流程
    
    使用示例:
        rag = RAGPipeline()
        
        # 入库
        rag.ingest(raw_document)
        
        # 检索 + 生成
        answer = rag.query("Redis分布式锁怎么实现？", memory_context="用户学过Redis基础")
    """
    
    def __init__(
        self,
        reranker_type: str = "none",
        use_hyde: bool = True,
    ):
        self.embedder = Embedder()
        self.chunker = AdaptiveChunker()
        self.vector_store = VectorStore(vector_size=self.embedder.dimension)
        self.retriever = HybridRetriever(
            vector_store=self.vector_store,
            embedder=self.embedder,
        )
        self.reranker: BaseReranker = get_reranker(reranker_type)
        self.use_hyde = use_hyde
        
        # LLM 客户端
        config = get_llm_config()
        self.llm_client = OpenAI(
            api_key=config["api_key"],
            base_url=config["base_url"],
        )
        self.llm_model = config["model"]
    
    # ============ 入库流程 ============
    
    def ingest(self, doc: RawDocument) -> list[str]:
        """
        文档入库
        
        Args:
            doc: 原始文档
        
        Returns:
            chunk ID 列表
        """
        # 1. 分块
        chunks = self.chunker.chunk(doc)
        
        # 2. Embedding
        contents = [c.content for c in chunks]
        embeddings = self.embedder.embed(contents)
        
        for chunk, embedding in zip(chunks, embeddings):
            chunk.embedding = embedding
        
        # 3. 存入向量数据库
        self.vector_store.add_documents(chunks)
        
        # 4. 添加到 BM25 索引
        self.retriever.add_to_bm25_index(chunks)
        
        return [c.id for c in chunks]
    
    def ingest_batch(self, docs: list[RawDocument]) -> int:
        """批量入库"""
        total = 0
        for doc in docs:
            chunk_ids = self.ingest(doc)
            total += len(chunk_ids)
        return total
    
    # ============ 检索流程 ============
    
    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        domain: str = None,
        use_rerank: bool = True,
    ) -> list[DocumentChunk]:
        """
        检索相关文档
        
        Args:
            query: 查询文本
            top_k: 返回数量
            domain: 过滤领域
            use_rerank: 是否使用重排序
        
        Returns:
            相关文档列表
        """
        # 1. HyDE 查询改写（可选）
        search_query = query
        if self.use_hyde:
            search_query = self._hyde_transform(query)
        
        # 2. 混合检索
        candidates = self.retriever.retrieve(
            query=search_query,
            top_k=top_k * 2 if use_rerank else top_k,
            domain=domain,
        )
        
        # 3. 重排序（可选）
        if use_rerank and candidates:
            candidates = self.reranker.rerank(query, candidates, top_k=top_k)
        
        return candidates[:top_k]
    
    def _hyde_transform(self, query: str) -> str:
        """
        HyDE: 假设性文档嵌入
        让 LLM 先生成一个假设答案，用答案去检索
        """
        prompt = f"""请针对以下问题，写一段简短的技术回答（100字左右）。
这个回答将用于检索相关文档，所以要包含关键技术术语。

问题：{query}

回答："""

        try:
            response = self.llm_client.chat.completions.create(
                model=self.llm_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=200,
            )
            hyde_answer = response.choices[0].message.content.strip()
            # 组合原始 query 和假设答案
            return f"{query}\n{hyde_answer}"
        except Exception:
            return query
    
    # ============ 生成流程 ============
    
    def query(
        self,
        question: str,
        memory_context: str = None,
        domain: str = None,
        top_k: int = 5,
    ) -> dict:
        """
        完整的 RAG 查询：检索 + 生成
        
        Args:
            question: 用户问题
            memory_context: 记忆上下文（来自 MemoryManager）
            domain: 过滤领域
            top_k: 检索数量
        
        Returns:
            {
                "answer": "...",
                "sources": [...],
            }
        """
        # 1. 检索
        chunks = self.retrieve(question, top_k=top_k, domain=domain)
        
        # 2. 构建上下文
        context_parts = []
        
        # 记忆上下文
        if memory_context:
            context_parts.append(f"【用户学习背景】\n{memory_context}")
        
        # 检索结果
        if chunks:
            context_parts.append("【相关知识】")
            for i, chunk in enumerate(chunks, 1):
                source_info = f"[来源: {chunk.source}]" if chunk.source else ""
                context_parts.append(f"{i}. {chunk.content} {source_info}")
        
        context = "\n\n".join(context_parts)
        
        # 3. 生成回答
        answer = self._generate_answer(question, context)
        
        return {
            "answer": answer,
            "sources": chunks,
        }
    
    def _generate_answer(self, question: str, context: str) -> str:
        """生成回答"""
        system_prompt = """你是一个面试辅导助手，帮助用户准备技术面试。

要求：
1. 基于提供的上下文回答问题
2. 如果用户有学习背景，根据其掌握程度调整回答深度
3. 回答要准确、有条理
4. 如果上下文信息不足，可以补充你的知识，但要说明"""

        user_prompt = f"""上下文信息：
{context}

用户问题：{question}

请回答："""

        response = self.llm_client.chat.completions.create(
            model=self.llm_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7,
        )
        
        return response.choices[0].message.content.strip()
    
    # ============ 工具方法 ============
    
    def get_stats(self) -> dict:
        """获取 RAG 统计信息"""
        vector_info = self.vector_store.get_collection_info()
        return {
            "vector_store": vector_info,
            "bm25_docs": len(self.retriever._bm25_chunks),
            "use_hyde": self.use_hyde,
            "reranker": type(self.reranker).__name__,
        }
