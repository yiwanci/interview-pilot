"""
RAG 系统测试
"""
import pytest
from unittest.mock import Mock, patch

from rag import Embedder, AdaptiveChunker, HybridRetriever, RAGPipeline
from storage import RawDocument, DocumentChunk


class TestEmbedder:
    """Embedding 测试"""
    
    @pytest.fixture
    def mock_embedder(self, mocker):
        """Mock OpenAI 客户端"""
        mock_response = Mock()
        mock_response.data = [
            Mock(embedding=[0.1] * 1536),
            Mock(embedding=[0.2] * 1536),
        ]
        
        mocker.patch('rag.embedder.OpenAI')
        embedder = Embedder()
        embedder.client.embeddings.create = Mock(return_value=mock_response)
        
        return embedder
    
    def test_embed_single(self, mock_embedder):
        """单条 Embedding"""
        result = mock_embedder.embed_single("测试文本")
        
        assert len(result) == 1536
        assert result[0] == 0.1
    
    def test_embed_batch(self, mock_embedder):
        """批量 Embedding"""
        results = mock_embedder.embed(["文本1", "文本2"])
        
        assert len(results) == 2
        assert len(results[0]) == 1536
    
    def test_embed_empty(self, mock_embedder):
        """空列表"""
        results = mock_embedder.embed([])
        assert results == []


class TestAdaptiveChunker:
    """自适应分块测试"""
    
    @pytest.fixture
    def chunker(self, mocker):
        """Mock LLM"""
        mocker.patch('rag.chunker.OpenAI')
        return AdaptiveChunker()
    
    def test_chunk_leetcode(self, chunker):
        """LeetCode 分块（整题一个 chunk）"""
        doc = RawDocument(
            id="lc-1",
            source="leetcode",
            url="https://leetcode.cn/problems/two-sum/",
            title="两数之和",
            content="给定一个整数数组 nums 和一个整数目标值 target...",
            metadata={"tags": ["数组", "哈希表"]}
        )
        
        chunks = chunker._chunk_leetcode(doc)
        
        assert len(chunks) == 1
        assert chunks[0].chunk_type == "algorithm"
        assert chunks[0].domain == "cs_basic"
    
    def test_chunk_fixed(self, chunker):
        """固定长度分块"""
        doc = RawDocument(
            id="doc-1",
            source="manual",
            url="",
            title="测试文档",
            content="这是一段很长的文本。" * 100,
        )
        
        chunks = chunker._chunk_fixed(doc, chunk_size=200, overlap=20)
        
        assert len(chunks) > 1
        for chunk in chunks:
            assert len(chunk.content) <= 250  # 允许一定余量
    
    def test_infer_domain(self, chunker):
        """领域推断"""
        assert chunker._infer_domain("Spring Boot 自动配置原理") == "java_backend"
        assert chunker._infer_domain("LangChain Agent 开发") == "ai_agent"
        assert chunker._infer_domain("Transformer 注意力机制") == "llm_algorithm"
        assert chunker._infer_domain("二叉树遍历") == "cs_basic"
    
    def test_infer_category(self, chunker):
        """分类推断"""
        assert chunker._infer_category("HashMap 底层实现") == "java_basic"
        assert chunker._infer_category("MySQL 索引优化") == "database"
        assert chunker._infer_category("RAG 检索增强") == "rag"


class TestHybridRetriever:
    """混合检索测试"""
    
    @pytest.fixture
    def retriever(self, mocker):
        """Mock 依赖"""
        mock_embedder = Mock()
        mock_embedder.embed_single = Mock(return_value=[0.1] * 1536)
        
        mock_vector_store = Mock()
        mock_vector_store.search = Mock(return_value=[
            DocumentChunk(id="v1", doc_id="d1", content="向量结果1"),
            DocumentChunk(id="v2", doc_id="d2", content="向量结果2"),
        ])
        
        retriever = HybridRetriever(
            vector_store=mock_vector_store,
            embedder=mock_embedder
        )
        
        return retriever
    
    def test_vector_search(self, retriever):
        """向量检索"""
        results = retriever._vector_search("测试查询", top_k=5)
        
        assert len(results) == 2
        assert results[0].content == "向量结果1"
    
    def test_bm25_search(self, retriever):
        """BM25 检索"""
        # 构建索引
        chunks = [
            DocumentChunk(id="b1", doc_id="d1", content="Redis 持久化 RDB AOF"),
            DocumentChunk(id="b2", doc_id="d2", content="MySQL 索引 B+树"),
            DocumentChunk(id="b3", doc_id="d3", content="Redis 分布式锁 Redisson"),
        ]
        retriever.build_bm25_index(chunks)
        
        # 搜索
        results = retriever._bm25_search("Redis 持久化", top_k=2)
        
        assert len(results) <= 2
        # Redis 相关的应该排在前面
        assert "Redis" in results[0].content
    
    def test_rrf_score(self, retriever):
        """RRF 分数计算"""
        score_0 = retriever._rrf_score(0)
        score_1 = retriever._rrf_score(1)
        score_10 = retriever._rrf_score(10)
        
        # 排名越靠前分数越高
        assert score_0 > score_1 > score_10
    
    def test_hybrid_retrieve(self, retriever):
        """混合检索"""
        # 构建 BM25 索引
        chunks = [
            DocumentChunk(id="h1", doc_id="d1", content="测试内容1", domain="test"),
        ]
        retriever.build_bm25_index(chunks)
        
        results = retriever.retrieve("测试", top_k=5)
        
        assert len(results) > 0


class TestRAGPipeline:
    """RAG Pipeline 测试"""
    
    @pytest.fixture
    def rag(self, mocker):
        """Mock 所有依赖"""
        mocker.patch('rag.rag_pipeline.Embedder')
        mocker.patch('rag.rag_pipeline.VectorStore')
        mocker.patch('rag.rag_pipeline.AdaptiveChunker')
        mocker.patch('rag.rag_pipeline.HybridRetriever')
        mocker.patch('rag.rag_pipeline.OpenAI')
        
        return RAGPipeline()
    
    def test_ingest(self, rag):
        """文档入库"""
        # Mock chunker
        rag.chunker.chunk = Mock(return_value=[
            DocumentChunk(id="c1", doc_id="d1", content="分块1"),
            DocumentChunk(id="c2", doc_id="d1", content="分块2"),
        ])
        
        # Mock embedder
        rag.embedder.embed = Mock(return_value=[
            [0.1] * 1536,
            [0.2] * 1536,
        ])
        
        doc = RawDocument(
            id="d1",
            source="test",
            url="",
            title="测试",
            content="测试内容",
        )
        
        chunk_ids = rag.ingest(doc)
        
        assert len(chunk_ids) == 2
        rag.vector_store.add_documents.assert_called_once()
    
    def test_retrieve(self, rag):
        """检索"""
        rag.retriever.retrieve = Mock(return_value=[
            DocumentChunk(id="r1", doc_id="d1", content="检索结果"),
        ])
        
        results = rag.retrieve("测试查询", top_k=5)
        
        assert len(results) == 1
    
    def test_query(self, rag):
        """完整查询"""
        # Mock retrieve
        rag.retriever.retrieve = Mock(return_value=[
            DocumentChunk(id="r1", doc_id="d1", content="相关内容"),
        ])
        
        # Mock LLM
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="生成的回答"))]
        rag.llm_client.chat.completions.create = Mock(return_value=mock_response)
        
        result = rag.query("测试问题")
        
        assert "answer" in result
        assert "sources" in result
        assert result["answer"] == "生成的回答"


def run_tests():
    """运行测试"""
    pytest.main([__file__, "-v"])


if __name__ == "__main__":
    run_tests()
