"""
MCP 客户端（基于 langchain_mcp_adapters）
使用 LangChain 的 MCP 适配器连接服务器
"""
import asyncio
from typing import Dict, List, Optional, Any

try:
    from langchain_mcp_adapters.client import MultiServerMCPClient
    LANGCHAIN_MCP_AVAILABLE = True
except ImportError:
    LANGCHAIN_MCP_AVAILABLE = False
    MultiServerMCPClient = None


class LangChainMCPClient:
    """
    LangChain MCP 客户端

    使用 langchain_mcp_adapters 连接多个 MCP 服务器
    """

    def __init__(self, servers: Optional[Dict[str, Dict]] = None):
        """
        初始化 MCP 客户端

        Args:
            servers: 服务器配置字典
                {
                    "服务器名": {
                        "transport": "streamable_http",
                        "url": "http://localhost:18060/mcp",
                    }
                }
        """
        self.servers = servers or {}
        self._client: Optional[MultiServerMCPClient] = None
        self._tools: List[Any] = []
        self._available = False

    async def initialize(self):
        """初始化客户端并获取工具"""
        if not LANGCHAIN_MCP_AVAILABLE:
            print("[MCP] langchain_mcp_adapters 未安装")
            return False

        try:
            self._client = MultiServerMCPClient(self.servers)
            self._tools = await self._client.get_tools()
            self._available = True
            print(f"[MCP] 已连接，可用工具：{len(self._tools)}")
            return True

        except Exception as e:
            print(f"[MCP] 连接失败: {e}")
            return False

    def initialize_sync(self):
        """同步初始化"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self.initialize())
        finally:
            loop.close()

    def is_available(self) -> bool:
        """检查 MCP 是否可用"""
        return self._available

    def get_tools(self) -> List[Any]:
        """获取可用工具列表"""
        return self._tools

    def get_tool_names(self) -> List[str]:
        """获取工具名称列表"""
        return [tool.name for tool in self._tools]

    async def call_tool(
        self,
        tool_name: str,
        arguments: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """
        调用 MCP 工具

        Args:
            tool_name: 工具名称
            arguments: 工具参数

        Returns:
            工具执行结果
        """
        if not self._available or not self._client:
            raise RuntimeError("MCP 客户端未连接")

        # 查找工具
        tool = None
        for t in self._tools:
            if t.name == tool_name:
                tool = t
                break

        if not tool:
            raise ValueError(f"工具不存在: {tool_name}")

        try:
            return await tool.ainvoke(arguments or {})
        except Exception as e:
            print(f"[MCP] 工具调用失败: {tool_name} - {e}")
            raise

    def call_tool_sync(
        self,
        tool_name: str,
        arguments: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """同步调用工具"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self.call_tool(tool_name, arguments))
        finally:
            loop.close()

    async def cleanup(self):
        """清理连接"""
        if self._client:
            await self._client.close()
            self._available = False
