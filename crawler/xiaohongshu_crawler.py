"""
小红书爬虫
基于 MediaCrawler 或直接请求
"""
import re
import time
import json
from typing import Optional
import httpx

from storage import RawDocument
from .base_crawler import BaseCrawler


class XiaohongshuCrawler(BaseCrawler):
    """
    小红书爬虫
    
    注意：
    - 小红书反爬较严，建议配合 MediaCrawler 使用
    - 或者手动导出数据后用 load_from_file 加载
    
    使用示例:
        crawler = XiaohongshuCrawler()
        docs = crawler.search("Java面经", limit=10)
        
        # 或从文件加载
        docs = crawler.load_from_file("exported_notes.json")
    """
    
    SOURCE_NAME = "xiaohongshu"
    
    BASE_URL = "https://www.xiaohongshu.com"
    SEARCH_API = "https://edith.xiaohongshu.com/api/sns/web/v1/search/notes"
    
    def __init__(self, cookie: str = None):
        super().__init__()
        self.cookie = cookie
        self.client = httpx.Client(
            headers=self.headers,
            timeout=30,
            follow_redirects=True,
        )
        if cookie:
            self.client.headers["Cookie"] = cookie
    
    def search(self, keyword: str, limit: int = 20) -> list[RawDocument]:
        """
        搜索小红书笔记
        
        由于反爬限制，这里提供两种方式：
        1. 有 cookie：尝试调用 API
        2. 无 cookie：返回空，建议用 MediaCrawler 或手动导出
        """
        if not self.cookie:
            print("提示：小红书需要登录 cookie，建议使用 MediaCrawler 工具或手动导出")
            print("MediaCrawler: https://github.com/NanmiCoder/MediaCrawler")
            return []
        
        # 尝试搜索（可能被反爬）
        try:
            return self._search_with_api(keyword, limit)
        except Exception as e:
            print(f"搜索失败: {e}")
            return []
    
    def _search_with_api(self, keyword: str, limit: int) -> list[RawDocument]:
        """通过 API 搜索（需要有效 cookie）"""
        docs = []
        
        # 这里是简化实现，实际需要处理签名等
        params = {
            "keyword": keyword,
            "page": 1,
            "page_size": min(limit, 20),
            "search_id": "",
            "sort": "general",
            "note_type": 0,
        }
        
        response = self.client.get(self.SEARCH_API, params=params)
        
        if response.status_code != 200:
            return []
        
        data = response.json()
        items = data.get("data", {}).get("items", [])
        
        for item in items[:limit]:
            note_card = item.get("note_card", {})
            doc = self._create_document(
                url=f"{self.BASE_URL}/explore/{item.get('id', '')}",
                title=note_card.get("display_title", ""),
                content=note_card.get("desc", ""),
                author=note_card.get("user", {}).get("nickname", ""),
                likes=note_card.get("interact_info", {}).get("liked_count", 0),
                metadata={
                    "note_id": item.get("id"),
                    "type": note_card.get("type"),
                }
            )
            docs.append(doc)
        
        return docs
    
    def crawl_detail(self, url: str) -> Optional[RawDocument]:
        """爬取笔记详情"""
        try:
            response = self.client.get(url)
            if response.status_code != 200:
                return None
            
            # 解析页面内容
            html = response.text
            
            # 提取标题
            title_match = re.search(r'<title>([^<]+)</title>', html)
            title = title_match.group(1) if title_match else ""
            
            # 提取正文（简化处理）
            # 实际需要更复杂的解析
            content_match = re.search(r'"desc":"([^"]+)"', html)
            content = content_match.group(1) if content_match else ""
            content = content.encode().decode('unicode_escape')
            
            return self._create_document(
                url=url,
                title=title,
                content=content,
            )
        except Exception as e:
            print(f"爬取详情失败: {e}")
            return None
    
    def load_from_file(self, file_path: str) -> list[RawDocument]:
        """
        从导出文件加载
        支持 MediaCrawler 导出的 JSON 格式
        
        Args:
            file_path: JSON 文件路径
        
        Returns:
            文档列表
        """
        docs = []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 支持列表或字典格式
        items = data if isinstance(data, list) else data.get("notes", [])
        
        for item in items:
            doc = self._create_document(
                url=item.get("url", item.get("note_url", "")),
                title=item.get("title", item.get("display_title", "")),
                content=item.get("content", item.get("desc", "")),
                author=item.get("author", item.get("nickname", "")),
                likes=item.get("likes", item.get("liked_count", 0)),
                metadata={
                    "note_id": item.get("note_id", item.get("id")),
                    "tags": item.get("tags", []),
                }
            )
            docs.append(doc)
        
        return docs
    
    def load_from_text(self, text: str, title: str = "手动输入") -> RawDocument:
        """
        从文本直接创建文档
        用于手动粘贴面经内容
        """
        return self._create_document(
            url="manual_input",
            title=title,
            content=text,
        )
