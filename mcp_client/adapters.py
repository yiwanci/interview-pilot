"""
MCP 工具适配器
将 MCP 工具转换为项目可用的接口
"""
from typing import Dict, List, Optional, Any
from storage.models import RawDocument
import json


class MCPCrawlerAdapter:
    """
    MCP 爬虫适配器

    将 MCP 工具转换为统一的爬虫接口
    """

    def __init__(self, mcp_manager=None):
        """
        初始化适配器

        Args:
            mcp_manager: MCP 管理器实例
        """
        from .manager import MCPManager

        self.mcp_manager = mcp_manager or MCPManager()

    def is_available(self) -> bool:
        """检查 MCP 爬虫是否可用"""
        return self.mcp_manager.is_available()

    def crawl(
        self,
        source: str,
        keyword: str,
        limit: int = 20,
        **kwargs,
    ) -> List[RawDocument]:
        """
        使用 MCP 爬取数据

        Args:
            source: 数据源（xiaohongshu/douyin/github/...）
            keyword: 搜索关键词
            limit: 数量限制
            **kwargs: 其他参数

        Returns:
            爬取的文档列表
        """
        if not self.is_available():
            raise RuntimeError("MCP 爬虫不可用")

        # 根据来源选择不同的 MCP 工具
        tool_mapping = {
            "xiaohongshu": "search_xiaohongshu",
            "xhs": "search_xiaohongshu",
            "douyin": "search_douyin",
            "dy": "search_douyin",
        }

        # 查找工具名
        tool_name = None
        for pattern, name in tool_mapping.items():
            if pattern in source.lower():
                tool_name = name
                break

        if not tool_name:
            tool_name = f"search_{source}"

        # 检查工具是否存在
        available_tools = self.mcp_manager.get_tool_names()
        if tool_name not in available_tools:
            # 尝试其他可能的工具名
            for t in available_tools:
                if source.lower() in t.lower():
                    tool_name = t
                    break
            else:
                raise ValueError(f"找不到 {source} 对应的 MCP 工具")

        # 调用 MCP 工具
        arguments = {
            "query": keyword,
            "limit": limit,
            **kwargs,
        }

        try:
            result = self.mcp_manager.call_tool_sync(
                tool_name=tool_name,
                arguments=arguments,
            )

            # 转换为 RawDocument
            return self._convert_to_documents(result, source)

        except Exception as e:
            print(f"[MCP] 爬取失败: {e}")
            return []

    def _convert_to_documents(
        self,
        raw_data: Any,
        source: str,
    ) -> List[RawDocument]:
        """
        将 MCP 返回的数据转换为 RawDocument

        Args:
            raw_data: MCP 工具返回的数据（可能是字符串、字典、列表）
            source: 数据源

        Returns:
            RawDocument 列表
        """
        documents = []

        # 如果返回的是字符串（如 Markdown 格式）
        if isinstance(raw_data, str):
            # 尝试从 Markdown 中提取内容
            docs = self._parse_markdown_to_docs(raw_data, source)
            documents.extend(docs)

        # 如果返回的是列表
        elif isinstance(raw_data, list):
            for item in raw_data:
                doc = self._convert_single_doc(item, source)
                if doc:
                    documents.append(doc)

        # 如果返回的是字典
        elif isinstance(raw_data, dict):
            doc = self._convert_single_doc(raw_data, source)
            if doc:
                documents.append(doc)

        return documents

    def _convert_single_doc(
        self,
        item: Dict,
        source: str,
    ) -> Optional[RawDocument]:
        """
        转换单个文档

        Args:
            item: 文档数据字典
            source: 数据源

        Returns:
            RawDocument 或 None
        """
        if not item:
            return None

        # 尝试从字典中提取字段
        title = item.get("title") or item.get("subject") or ""
        content = item.get("content") or item.get("body") or item.get("text") or ""
        url = item.get("url") or item.get("link") or ""
        author = item.get("author") or item.get("user") or ""

        if not content:
            return None

        return RawDocument(
            id=item.get("id", ""),
            source=source,
            url=url,
            title=title or f"未命名文档",
            content=content,
            author=author,
            likes=item.get("likes", 0),
            metadata={
                "raw": item,
                "platform": item.get("platform", source),
            },
        )

    def _parse_markdown_to_docs(
        self,
        markdown_text: str,
        source: str,
    ) -> List[RawDocument]:
        """
        解析 Markdown 文本为文档列表

        Args:
            markdown_text: Markdown 文本
            source: 数据源

        Returns:
            RawDocument 列表
        """
        documents = []

        # 简单的 Markdown 解析
        # 查找 ## 标题
        lines = markdown_text.split("\n")
        current_title = ""
        current_content = []

        for line in lines:
            line = line.strip()

            # ## 标题
            if line.startswith("## "):
                # 保存之前的文档
                if current_content:
                    content = "\n".join(current_content).strip()
                    if content:
                        documents.append(RawDocument(
                            id="",
                            source=source,
                            url="",
                            title=current_title or "未知标题",
                            content=content,
                            author="",
                            likes=0,
                            metadata={"platform": source},
                        ))

                # 开始新文档
                current_title = line[3:].strip()
                current_content = []
            elif line.startswith("# "):
                # 忽略一级标题
                continue
            elif line:
                current_content.append(line)

        # 保存最后一个文档
        if current_content:
            content = "\n".join(current_content).strip()
            if content:
                documents.append(RawDocument(
                    id="",
                    source=source,
                    url="",
                    title=current_title or "未知标题",
                    content=content,
                    author="",
                    likes=0,
                    metadata={"platform": source},
                ))

        return documents

    def list_sources(self) -> List[str]:
        """
        列出支持的爬虫来源

        Returns:
            来源列表
        """
        if not self.is_available():
            return []

        tool_names = self.mcp_manager.get_tool_names()

        sources = set()
        for tool_name in tool_names:
            # 从工具名中提取来源
            if "xiaohongshu" in tool_name.lower() or "xhs" in tool_name.lower():
                sources.add("xiaohongshu")
            elif "douyin" in tool_name.lower() or "dy" in tool_name.lower():
                sources.add("douyin")
            elif "github" in tool_name.lower():
                sources.add("github")
            elif "web" in tool_name.lower():
                sources.add("web")

        return list(sources)

    def get_source_info(self, source: str) -> Optional[Dict]:
        """
        获取来源信息

        Args:
            source: 来源名称

        Returns:
            来源信息字典
        """
        if not self.is_available():
            return None

        sources = self.list_sources()
        if source not in sources:
            return None

        return {
            "name": source,
            "supported": True,
        }


# ==================== 工厂函数 ====================

def create_mcp_crawler_adapter() -> Optional[MCPCrawlerAdapter]:
    """
    创建 MCP 爬虫适配器

    Returns:
        适配器实例，如果 MCP 不可用则返回 None
    """
    from .manager import MCPManager

    manager = MCPManager()
    manager.initialize_sync()

    if manager.is_available():
        return MCPCrawlerAdapter(manager)

    return None
