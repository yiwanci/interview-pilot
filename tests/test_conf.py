"""
Pytest 配置和共享 fixtures
"""
import pytest
import sys
from pathlib import Path

# 确保项目根目录在路径中
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))


@pytest.fixture(scope="session")
def project_root():
    """项目根目录"""
    return ROOT_DIR


@pytest.fixture
def sample_raw_document():
    """示例原始文档"""
    from storage import RawDocument
    
    return RawDocument(
        id="sample-1",
        source="xiaohongshu",
        url="https://example.com/note/1",
        title="字节跳动一面面经",
        content="""
        字节跳动后端一面，总共问了5个问题：
        
        1. HashMap底层原理？
        答：数组+链表+红黑树，负载因子0.75，扩容2倍
        
        2. Redis持久化机制？
        答：RDB快照和AOF日志两种方式
        
        3. TCP三次握手？
        答：SYN -> SYN+ACK -> ACK
        
        4. Spring IOC原理？
        答：控制反转，依赖注入，Bean容器管理
        
        5. 手撕算法：两数之和
        答：用HashMap，时间复杂度O(n)
        
        整体难度中等，面试官很nice
        """,
        author="面试小能手",
        likes=1234,
        metadata={
            "company": "字节跳动",
            "position": "后端开发",
            "round": "一面",
        }
    )


@pytest.fixture
def sample_document_chunks():
    """示例文档分块"""
    from storage import DocumentChunk
    
    return [
        DocumentChunk(
            id="chunk-1",
            doc_id="sample-1",
            content="HashMap底层原理：数组+链表+红黑树，负载因子0.75，扩容2倍",
            chunk_type="qa",
            source="xiaohongshu",
            domain="java_backend",
            category="java_basic",
            question="HashMap底层原理？",
            answer="数组+链表+红黑树，负载因子0.75，扩容2倍",
            company="字节跳动",
            tags=["Java", "集合框架"],
        ),
        DocumentChunk(
            id="chunk-2",
            doc_id="sample-1",
            content="Redis持久化机制：RDB快照和AOF日志两种方式",
            chunk_type="qa",
            source="xiaohongshu",
            domain="java_backend",
            category="database",
            question="Redis持久化机制？",
            answer="RDB快照和AOF日志两种方式",
            company="字节跳动",
            tags=["Redis", "持久化"],
        ),
        DocumentChunk(
            id="chunk-3",
            doc_id="sample-1",
            content="TCP三次握手：SYN -> SYN+ACK -> ACK",
            chunk_type="qa",
            source="xiaohongshu",
            domain="cs_basic",
            category="network",
            question="TCP三次握手？",
            answer="SYN -> SYN+ACK -> ACK",
            company="字节跳动",
            tags=["TCP", "网络"],
        ),
    ]


@pytest.fixture
def sample_knowledge_points():
    """示例知识点"""
    from storage import KnowledgePoint
    from datetime import datetime, timedelta
    
    return [
        KnowledgePoint(
            id="kp-1",
            name="HashMap底层原理",
            category="java_basic",
            domain="java_backend",
            tags=["Java", "集合框架"],
            difficulty=3,
            mastery_level=0.3,
            repetitions=1,
            next_review_at=datetime.now() - timedelta(days=1),  # 已到期
        ),
        KnowledgePoint(
            id="kp-2",
            name="Redis持久化",
            category="database",
            domain="java_backend",
            tags=["Redis", "持久化"],
            difficulty=3,
            mastery_level=0.7,
            repetitions=3,
            next_review_at=datetime.now() + timedelta(days=5),  # 未到期
        ),
        KnowledgePoint(
            id="kp-3",
            name="TCP三次握手",
            category="network",
            domain="cs_basic",
            tags=["TCP", "网络"],
            difficulty=2,
            mastery_level=0.9,
            repetitions=5,
            next_review_at=datetime.now() + timedelta(days=30),  # 已掌握
        ),
    ]


@pytest.fixture
def mock_llm_response():
    """Mock LLM 响应"""
    from unittest.mock import Mock
    
    def create_response(content: str):
        response = Mock()
        response.choices = [Mock(message=Mock(content=content))]
        return response
    
    return create_response


@pytest.fixture
def mock_embedding():
    """Mock Embedding"""
    def create_embedding(dim: int = 1536):
        return [0.1] * dim
    
    return create_embedding


@pytest.fixture
def temp_db(tmp_path):
    """临时数据库"""
    from storage import SQLiteStore
    
    db_path = tmp_path / "test.db"
    return SQLiteStore(db_path=db_path)


@pytest.fixture
def temp_data_dir(tmp_path):
    """临时数据目录"""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "raw").mkdir()
    return data_dir
