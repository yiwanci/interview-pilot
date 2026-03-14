"""
Embedding 封装
支持切换不同的 Embedding 模型
"""
from openai import OpenAI

from config import get_llm_config, LLM_PROVIDER


class Embedder:
    """
    Embedding 封装类
    """
    
    # 通义千问 embedding-v3 支持的维度
    QWEN_DIMENSIONS = [64, 128, 256, 512, 768, 1024]
    DEFAULT_DIMENSION = 1024  # 默认使用 1024 维
    
    def __init__(self, dimension: int = None):
        config = get_llm_config()
        self.client = OpenAI(
            api_key=config["api_key"],
            base_url=config["base_url"],
        )
        self.model = config["embedding_model"]
        self._dimension = dimension or self.DEFAULT_DIMENSION
        self._provider = LLM_PROVIDER
    
    @property
    def dimension(self) -> int:
        """获取向量维度"""
        return self._dimension
    
    def embed(self, texts: list[str]) -> list[list[float]]:
        """批量 Embedding"""
        if not texts:
            return []
        
        texts = [t if t else " " for t in texts]
        
        # 通义千问需要指定维度
        if self._provider == "qwen" and "v3" in self.model:
            response = self.client.embeddings.create(
                model=self.model,
                input=texts,
                dimensions=self._dimension,
            )
        else:
            response = self.client.embeddings.create(
                model=self.model,
                input=texts,
            )
        
        return [item.embedding for item in response.data]
    
    def embed_single(self, text: str) -> list[float]:
        """单条 Embedding"""
        results = self.embed([text])
        return results[0] if results else []
