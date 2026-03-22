"""
MCP 爬虫包装器
使用 LangChain Agent 自动选择工具
"""
import json
import asyncio
import logging
from typing import Dict, List, Optional, Any
from storage.models import RawDocument

# 配置日志
logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        '[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


class MCPCrawlerWrapper:
    """
    MCP 爬虫包装器

    使用 LangChain Agent，让 LLM 自动选择和调用工具
    """

    def __init__(self):
        """初始化包装器"""
        try:
            from langchain_mcp_adapters.client import MultiServerMCPClient
            from langchain.agents import create_agent
            from langchain_community.chat_models import ChatTongyi
            from config import get_llm_config

            # 1. 创建 MCP 客户端
            self._client = MultiServerMCPClient(self._load_servers_config())
            logger.info("[MCP] 客户端创建成功")

            # 2. 创建 LLM
            llm_config = get_llm_config()
            self._llm = ChatTongyi(
                model=llm_config["model"],
                api_key=llm_config["api_key"],
            )
            logger.info(f"[MCP] LLM 配置: {llm_config['model']}")

            # 3. 创建 Agent（工具在 initialize 中获取）
            self._agent = None
            self._tools: List[Any] = []
            self._available = False

        except ImportError as e:
            logger.warning(f"[MCP] 导入失败: {e}")
            self._client = None
            self._agent = None
            self._llm = None
            self._tools = []
            self._available = False

    def initialize(self):
        """初始化并连接 MCP 服务器"""
        if not self._client:
            logger.warning("[MCP] 客户端未初始化")
            return False

        from langchain.agents import create_agent

        async def _init():
            try:
                # 获取工具
                logger.info("[MCP] 正在获取工具列表...")
                self._tools = await self._client.get_tools()
                logger.info(f"[MCP] 获取到 {len(self._tools)} 个工具")

                # 创建 Agent（传入 LLM + 所有工具）
                self._agent = create_agent(self._llm, self._tools)
                logger.info("[MCP] Agent 创建成功")

                self._available = True
                logger.info(f"[MCP] 已连接，工具数量：{len(self._tools)}")
                return True
            except Exception as e:
                logger.error(f"[MCP] 连接失败: {e}", exc_info=True)
                return False

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(_init())
        finally:
            loop.close()

    def is_available(self) -> bool:
        """检查 MCP 是否可用"""
        return self._available

    def get_tools(self) -> List[Any]:
        """获取可用工具"""
        return self._tools

    def get_tool_names(self) -> List[str]:
        """获取工具名称列表"""
        return [tool.name for tool in self._tools]

    def crawl_direct(self, user_input: str) -> str:
        """
        直接调用 Agent，返回原始内容

        Args:
            user_input: 用户原始输入

        Returns:
            Agent 返回的原始内容字符串
        """
        if not self._available or not self._agent:
            raise RuntimeError("MCP 不可用")

        logger.info(f"[MCP] crawl_direct: {user_input[:50]}...")

        # 直接调用 Agent 并返回原始内容
        return self._call_agent_sync(user_input)

    def crawl(
        self,
        source: str,
        keyword: str,
        limit: int = 20,
        **kwargs,
    ) -> List[RawDocument]:
        """
        爬取数据（让 Agent 自动选择工具）

        Args:
            source: 数据源（xiaohongshu/douyin/...）
            keyword: 搜索关键词
            limit: 数量限制
            **kwargs: 其他参数

        Returns:
            爬取的文档列表
        """
        if not self._available or not self._agent:
            raise RuntimeError("MCP 不可用")

        # 构建提示词
        prompt = self._build_crawl_prompt(source, keyword, limit, **kwargs)

        # 调用 Agent（让它自己选择工具）
        result = self._call_agent_sync(prompt)

        # 解析结果
        return self._parse_agent_result(result, source)

    def _build_crawl_prompt(
        self,
        source: str,
        keyword: str,
        limit: int,
        **kwargs,
    ) -> str:
        """构建爬虫提示词"""
        source_name = {
            "xiaohongshu": "小红书",
            "xhs": "小红书",
            "douyin": "抖音",
            "dy": "抖音",
            "github": "GitHub",
            "web": "网页",
        }.get(source.lower(), source)

        prompt = f"""请搜索并获取与「{keyword}」相关的 {source_name} 内容。

要求：
1. 返回前 {limit} 条结果
2. 每条结果包含：标题、内容、链接（如果有的话）
3. 不要提及其他无关内容
4. 如果结果是 Markdown 格式，请直接输出
5. 如果是 JSON 格式，请直接输出

开始搜索："""
        return prompt

    def _call_agent_sync(self, prompt: str) -> str:
        """同步调用 Agent"""
        async def _call():
            try:
                result = await self._agent.ainvoke({
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt,
                        }
                    ]
                })

                # 提取响应内容
                if isinstance(result, dict) and "messages" in result:
                    messages = result["messages"]
                    if messages:
                        last_msg = messages[-1]
                        content = getattr(last_msg, "content", "")
                        if isinstance(content, list):
                            # 如果 content 是列表，拼接
                            return "".join(str(c) for c in content)
                        return str(content)
                return str(result)
            except Exception as e:
                print(f"[MCP] Agent 调用失败: {e}")
                raise

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(_call())
        finally:
            loop.close()

    def _parse_agent_result(
        self,
        result: str,
        source: str,
    ) -> List[RawDocument]:
        """解析 Agent 返回结果"""
        documents = []

        # 尝试解析为 JSON
        try:
            data = json.loads(result)
            if isinstance(data, list):
                for item in data:
                    doc = self._convert_single_doc(item, source)
                    if doc:
                        documents.append(doc)
                return documents
        except (json.JSONDecodeError, ValueError):
            pass

        # 解析 Markdown 格式
        docs = self._parse_markdown_to_docs(result, source)
        documents.extend(docs)

        return documents

    def _convert_single_doc(
        self,
        item: Dict,
        source: str,
    ) -> Optional[RawDocument]:
        """转换单个文档"""
        if not item:
            return None

        # 提取字段
        title = (
            item.get("title")
            or item.get("subject")
            or item.get("name")
            or ""
        )
        content = (
            item.get("content")
            or item.get("body")
            or item.get("text")
            or item.get("description")
            or ""
        )
        url = item.get("url") or item.get("link") or item.get("href") or ""
        author = (
            item.get("author")
            or item.get("user")
            or item.get("username")
            or ""
        )

        if not content:
            return None

        return RawDocument(
            id=item.get("id", ""),
            source=source,
            url=url,
            title=title or "未命名文档",
            content=content,
            author=author,
            likes=item.get("likes", item.get("like_count", 0)),
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
        """解析 Markdown 文本为文档列表"""
        documents = []

        # 简单的 Markdown 解析
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
                        documents.append(
                            RawDocument(
                                id="",
                                source=source,
                                url="",
                                title=current_title or "未知标题",
                                content=content,
                                author="",
                                likes=0,
                                metadata={"platform": source},
                            )
                        )

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
                documents.append(
                    RawDocument(
                        id="",
                        source=source,
                        url="",
                        title=current_title or "未知标题",
                        content=content,
                        author="",
                        likes=0,
                        metadata={"platform": source},
                    )
                )

        return documents

    def list_supported_sources(self) -> List[str]:
        """列出支持的数据源"""
        if not self._available:
            return []

        # 根据服务器配置返回支持的来源
        import os
        sources = []

        if os.getenv("MCP_XIAOHONGSHU_ENABLED", "false").lower() in ["true", "1"]:
            sources.append("xiaohongshu")

        if os.getenv("MCP_DOUYIN_ENABLED", "false").lower() in ["true", "1"]:
            sources.append("douyin")

        # 如果有工具但环境变量没配置，从工具名推断
        if not sources and self._tools:
            for tool in self._tools:
                tool_name = tool.name.lower()
                if "xiaohongshu" in tool_name or "xhs" in tool_name:
                    if "xhs" not in sources:
                        sources.append("xiaohongshu")
                elif "douyin" in tool_name or "dy" in tool_name:
                    if "douyin" not in sources:
                        sources.append("douyin")

        return sorted(list(sources))

    def _load_servers_config(self) -> Dict[str, Dict]:
        """从环境变量加载 MCP 服务器配置"""
        import os

        servers = {}

        # 小红书 MCP 服务器
        if os.getenv("MCP_XIAOHONGSHU_ENABLED", "false").lower() in ["true", "1"]:
            url = os.getenv(
                "MCP_XIAOHONGSHU_URL", "http://localhost:18060/mcp"
            )
            servers["xiaohongshu"] = {
                "transport": "streamable_http",
                "url": url,
            }

        # 抖音 MCP 服务器
        if os.getenv("MCP_DOUYIN_ENABLED", "false").lower() in ["true", "1"]:
            url = os.getenv("MCP_DOUYIN_URL", "http://localhost:18061/mcp")
            servers["douyin"] = {
                "transport": "streamable_http",
                "url": url,
            }

        return servers


# 工厂函数
def create_mcp_crawler() -> Optional[MCPCrawlerWrapper]:
    """创建 MCP 爬虫实例"""
    crawler = MCPCrawlerWrapper()
    if crawler.initialize():
        return crawler
    return None
