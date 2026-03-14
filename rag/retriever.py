"""
混合检索器
BM25 + 向量检索 + RRF 融合
"""
from typing import Optional
from rank_bm25 import BM25Okapi
import jieba

from storage import VectorStore, DocumentChunk
from .embedder import Embedder


class HybridRetriever:
    """
    混合检索器
    
    策略：
    1. BM25 关键词检索
    2. 向量语义检索
    3. RRF (Reciprocal Rank Fusion) 融合排序
    
    使用示例:
        retriever = HybridRetriever()
        results = retriever.retrieve("Redis分布式锁怎么实现", top_k=5)
    """
    
    def __init__(self, vector_store: VectorStore = None, embedder: Embedder = None):
        self.embedder = embedder or Embedder()
        self.vector_store = vector_store or VectorStore(vector_size=self.embedder.dimension)
        
        # BM25 索引（内存中）
        self._bm25_corpus = []      # 原始文档列表
        self._bm25_index = None     # BM25 索引
        self._bm25_chunks = []      # chunk 列表（和 corpus 对应）
    
    def retrieve(
        self,
        query: str,
        top_k: int = 10,
        domain: str = None,
        use_bm25: bool = True,
        use_vector: bool = True,
        bm25_weight: float = 0.3,
        vector_weight: float = 0.7,
    ) -> list[DocumentChunk]:
        """
        混合检索
        
        Args:
            query: 查询文本
            top_k: 返回数量
            domain: 过滤领域
            use_bm25: 是否使用 BM25
            use_vector: 是否使用向量检索
            bm25_weight: BM25 权重
            vector_weight: 向量检索权重
        
        Returns:
            检索结果列表
        """
        results = {}  # chunk_id -> {"chunk": chunk, "score": score}
        
        # 1. 向量检索
        if use_vector:
            vector_results = self._vector_search(query, top_k=top_k * 2, domain=domain)
            for rank, chunk in enumerate(vector_results):
                rrf_score = self._rrf_score(rank) * vector_weight
                if chunk.id in results:
                    results[chunk.id]["score"] += rrf_score
                else:
                    results[chunk.id] = {"chunk": chunk, "score": rrf_score}
        
        # 2. BM25 检索
        if use_bm25 and self._bm25_index:
            bm25_results = self._bm25_search(query, top_k=top_k * 2, domain=domain)
            for rank, chunk in enumerate(bm25_results):
                rrf_score = self._rrf_score(rank) * bm25_weight
                if chunk.id in results:
                    results[chunk.id]["score"] += rrf_score
                else:
                    results[chunk.id] = {"chunk": chunk, "score": rrf_score}
        
        # 3. 按分数排序
        sorted_results = sorted(
            results.values(),
            key=lambda x: x["score"],
            reverse=True
        )
        
        return [r["chunk"] for r in sorted_results[:top_k]]
    
    def _vector_search(
        self,
        query: str,
        top_k: int,
        domain: str = None,
    ) -> list[DocumentChunk]:
        """向量检索"""
        query_vector = self.embedder.embed_single(query)
        return self.vector_store.search(
            query_vector=query_vector,
            top_k=top_k,
            domain=domain,
        )
    
    def _bm25_search(
        self,
        query: str,
        top_k: int,
        domain: str = None,
    ) -> list[DocumentChunk]:
        """BM25 检索"""
        if not self._bm25_index:
            return []
        
        # 分词
        query_tokens = list(jieba.cut(query))
        
        # 检索
        scores = self._bm25_index.get_scores(query_tokens)
        
        # 排序
        scored_chunks = list(zip(self._bm25_chunks, scores))
        
        # 过滤领域
        if domain:
            scored_chunks = [(c, s) for c, s in scored_chunks if c.domain == domain]
        
        scored_chunks.sort(key=lambda x: x[1], reverse=True)
        
        return [c for c, s in scored_chunks[:top_k]]
    
    @staticmethod
    def _rrf_score(rank: int, k: int = 60) -> float:
        """
        RRF (Reciprocal Rank Fusion) 分数
        公式：1 / (k + rank)
        """
        return 1.0 / (k + rank + 1)
    
    # ============ 索引管理 ============
    
    def build_bm25_index(self, chunks: list[DocumentChunk]):
        """
        构建 BM25 索引
        
        Args:
            chunks: 文档分块列表
        """
        self._bm25_chunks = chunks
        self._bm25_corpus = []
        
        for chunk in chunks:
            # 分词
            tokens = list(jieba.cut(chunk.content))
            self._bm25_corpus.append(tokens)
        
        self._bm25_index = BM25Okapi(self._bm25_corpus)
    
    def add_to_bm25_index(self, chunks: list[DocumentChunk]):
        """增量添加到 BM25 索引"""
        for chunk in chunks:
            tokens = list(jieba.cut(chunk.content))
            self._bm25_corpus.append(tokens)
            self._bm25_chunks.append(chunk)
        
        # 重建索引（BM25Okapi 不支持增量）
        if self._bm25_corpus:
            self._bm25_index = BM25Okapi(self._bm25_corpus)
