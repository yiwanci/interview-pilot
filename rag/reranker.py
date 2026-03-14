"""
重排序器（预留接口）
后续可接入 BGE-Reranker / Cohere 等
"""
from abc import ABC, abstractmethod

from storage import DocumentChunk


class BaseReranker(ABC):
    """重排序器基类"""
    
    @abstractmethod
    def rerank(
        self,
        query: str,
        documents: list[DocumentChunk],
        top_k: int = 5,
    ) -> list[DocumentChunk]:
        """
        重排序
        
        Args:
            query: 查询文本
            documents: 待排序文档
            top_k: 返回数量
        
        Returns:
            重排序后的文档列表
        """
        pass


class NoOpReranker(BaseReranker):
    """
    空实现（不做重排序）
    用于占位，后续替换为真实实现
    """
    
    def rerank(
        self,
        query: str,
        documents: list[DocumentChunk],
        top_k: int = 5,
    ) -> list[DocumentChunk]:
        return documents[:top_k]


class BGEReranker(BaseReranker):
    """
    BGE Reranker（预留实现）
    需要本地部署模型或调用 API
    """
    
    def __init__(self, model_path: str = None):
        self.model_path = model_path
        self._model = None
        # TODO: 加载模型
    
    def rerank(
        self,
        query: str,
        documents: list[DocumentChunk],
        top_k: int = 5,
    ) -> list[DocumentChunk]:
        # TODO: 实现重排序逻辑
        # 1. 计算 query 和每个 doc 的相关性分数
        # 2. 按分数排序
        # 3. 返回 top_k
        
        # 暂时返回原顺序
        return documents[:top_k]


class CohereReranker(BaseReranker):
    """
    Cohere Reranker（预留实现）
    需要 Cohere API Key
    """
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key
        # TODO: 初始化 Cohere 客户端
    
    def rerank(
        self,
        query: str,
        documents: list[DocumentChunk],
        top_k: int = 5,
    ) -> list[DocumentChunk]:
        # TODO: 调用 Cohere Rerank API
        return documents[:top_k]


def get_reranker(reranker_type: str = "none", **kwargs) -> BaseReranker:
    """
    工厂方法：获取重排序器
    
    Args:
        reranker_type: "none" / "bge" / "cohere"
    """
    if reranker_type == "bge":
        return BGEReranker(**kwargs)
    elif reranker_type == "cohere":
        return CohereReranker(**kwargs)
    else:
        return NoOpReranker()
