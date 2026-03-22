"""
MCP 连接管理器
统一管理多个 MCP 服务器连接
"""
import os
import asyncio
from typing import Dict, Optional, List, Any
from dataclasses import dataclass
from .langchain_client import LangChainMCPClient


@dataclass
class MCPServerConfig:
    """MCP 服务器配置"""
    name: str
    transport: str = "streamable_http"
    url: str = ""
    command: str = ""
    args: List[str] = None
    enabled: bool = True


class MCPManager:
    """
    MCP 连接管理器

    功能：
    1. 管理多个 MCP 服务器连接
    2. 提供工具调用统一接口
    3. 支持工具发现和路由
    """

    _instance: Optional["MCPManager"] = None

    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """初始化管理器"""
        if hasattr(self, "_initialized"):
            return

        self._client: Optional[LangChainMCPClient] = None
        self._tools: List[Any] = []
        self._initialized = False

    async def initialize(self):
        """初始化所有启用的 MCP 服务器"""
        if self._initialized:
            return

        configs = self._load_configs()

        if not configs:
            print("[MCP] 未配置 MCP 服务器")
            return

        # 构建 LangChain MCP 客户端配置
        servers_config = {}
        for config in configs:
            if not config.enabled:
                continue

            if config.transport == "streamable_http" and config.url:
                servers_config[config.name] = {
                    "transport": "streamable_http",
                    "url": config.url,
                }
            elif config.transport == "stdio" and config.command:
                # stdio 模式暂未实现
                pass

        if not servers_config:
            print("[MCP] 没有可用的服务器配置")
            return

        # 初始化客户端
        self._client = LangChainMCPClient(servers_config)
        connected = await self._client.initialize()

        if connected:
            self._tools = self._client.get_tools()
            self._initialized = True
            print(f"[MCP] 初始化完成，已连接 {len(servers_config)} 个服务器，工具：{len(self._tools)}")

    def initialize_sync(self):
        """同步初始化"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self.initialize())
        finally:
            loop.close()

    def _load_configs(self) -> List[MCPServerConfig]:
        """从环境变量加载 MCP 服务器配置"""
        configs = []

        # 小红书 MCP 服务器
        if os.getenv("MCP_XIAOHONGSHU_ENABLED", "false").lower() == "true":
            url = os.getenv("MCP_XIAOHONGSHU_URL", "http://localhost:18060/mcp")
            configs.append(MCPServerConfig(
                name="xiaohongshu",
                transport="streamable_http",
                url=url,
                enabled=True,
            ))

        # 抖音 MCP 服务器
        if os.getenv("MCP_DOUYIN_ENABLED", "false").lower() == "true":
            url = os.getenv("MCP_DOUYIN_URL", "http://localhost:18061/mcp")
            configs.append(MCPServerConfig(
                name="douyin",
                transport="streamable_http",
                url=url,
                enabled=True,
            ))

        return configs

    def is_available(self) -> bool:
        """检查是否有 MCP 服务器可用"""
        return self._initialized and self._client and self._client.is_available()

    def get_all_tools(self) -> List[Any]:
        """获取所有可用工具"""
        return self._tools

    def get_tool_names(self) -> List[str]:
        """获取工具名称列表"""
        if self._client:
            return self._client.get_tool_names()
        return []

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
        if not self.is_available():
            raise RuntimeError("MCP 客户端未连接")

        return await self._client.call_tool(tool_name, arguments)

    def call_tool_sync(
        self,
        tool_name: str,
        arguments: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """同步调用工具"""
        if not self.is_available():
            raise RuntimeError("MCP 客户端未连接")

        return self._client.call_tool_sync(tool_name, arguments)

    async def cleanup(self):
        """清理所有连接"""
        if self._client:
            await self._client.cleanup()
            self._initialized = False
