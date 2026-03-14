"""
爬虫基类
定义统一接口
"""
from abc import ABC, abstractmethod
from typing import Optional
import uuid
from datetime import datetime

from storage import RawDocument


class BaseCrawler(ABC):
    """
    爬虫基类
    
    所有爬虫需要实现：
    - search(): 搜索关键词
    - crawl_detail(): 爬取详情页
    """
    
    # 子类需要设置
    SOURCE_NAME = "unknown"
    
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        }
    
    @abstractmethod
    def search(self, keyword: str, limit: int = 20) -> list[RawDocument]:
        """
        搜索关键词
        
        Args:
            keyword: 搜索关键词，如 "Java面经"
            limit: 返回数量
        
        Returns:
            文档列表
        """
        pass
    
    @abstractmethod
    def crawl_detail(self, url: str) -> Optional[RawDocument]:
        """
        爬取详情页
        
        Args:
            url: 详情页 URL
        
        Returns:
            文档对象
        """
        pass
    
    def _create_document(
        self,
        url: str,
        title: str,
        content: str,
        author: str = "",
        likes: int = 0,
        metadata: dict = None,
    ) -> RawDocument:
        """创建文档对象"""
        return RawDocument(
            id=str(uuid.uuid4()),
            source=self.SOURCE_NAME,
            url=url,
            title=title,
            content=content,
            author=author,
            likes=likes,
            crawled_at=datetime.now(),
            metadata=metadata or {},
        )
