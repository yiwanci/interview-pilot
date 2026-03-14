"""
抖音爬虫
主要爬取视频评论区的面经内容
"""
import json
from typing import Optional
import httpx

from storage import RawDocument
from .base_crawler import BaseCrawler


class DouyinCrawler(BaseCrawler):
    """
    抖音爬虫
    
    注意：
    - 抖音反爬非常严格
    - 建议使用 MediaCrawler 工具
    - 或手动导出后用 load_from_file 加载
    
    使用示例:
        crawler = DouyinCrawler()
        docs = crawler.load_from_file("douyin_export.json")
    """
    
    SOURCE_NAME = "douyin"
    
    def __init__(self, cookie: str = None):
        super().__init__()
        self.cookie = cookie
        self.client = httpx.Client(
            headers=self.headers,
            timeout=30,
        )
    
    def search(self, keyword: str, limit: int = 20) -> list[RawDocument]:
        """
        搜索抖音视频
        
        由于反爬限制，建议使用 MediaCrawler
        """
        print("提示：抖音反爬严格，建议使用 MediaCrawler 工具")
        print("MediaCrawler: https://github.com/NanmiCoder/MediaCrawler")
        return []
    
    def crawl_detail(self, url: str) -> Optional[RawDocument]:
        """爬取视频详情"""
        print("提示：请使用 MediaCrawler 或手动导出")
        return None
    
    def load_from_file(self, file_path: str) -> list[RawDocument]:
        """
        从导出文件加载
        
        Args:
            file_path: JSON 文件路径
        
        Returns:
            文档列表
        """
        docs = []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        items = data if isinstance(data, list) else data.get("videos", [])
        
        for item in items:
            # 合并视频描述和评论
            content_parts = []
            
            # 视频描述
            desc = item.get("desc", item.get("description", ""))
            if desc:
                content_parts.append(f"【视频描述】{desc}")
            
            # 评论内容（面经通常在评论区）
            comments = item.get("comments", [])
            if comments:
                content_parts.append("【评论区】")
                for comment in comments[:20]:  # 取前20条
                    comment_text = comment.get("text", comment.get("content", ""))
                    if comment_text and len(comment_text) > 20:  # 过滤太短的
                        content_parts.append(f"- {comment_text}")
            
            if not content_parts:
                continue
            
            doc = self._create_document(
                url=item.get("url", item.get("share_url", "")),
                title=item.get("title", desc[:50] if desc else "抖音视频"),
                content="\n".join(content_parts),
                author=item.get("author", item.get("nickname", "")),
                likes=item.get("likes", item.get("digg_count", 0)),
                metadata={
                    "video_id": item.get("video_id", item.get("aweme_id")),
                    "comment_count": len(comments),
                }
            )
            docs.append(doc)
        
        return docs
    
    def load_from_text(self, text: str, title: str = "抖音面经") -> RawDocument:
        """从文本直接创建文档"""
        return self._create_document(
            url="manual_input",
            title=title,
            content=text,
        )
