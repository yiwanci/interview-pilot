"""
MCP (Model Context Protocol) 集成模块
提供统一的 MCP 客户端和工具管理
"""

from .manager import MCPManager
from .langchain_client import LangChainMCPClient
from .adapters import MCPCrawlerAdapter, create_mcp_crawler_adapter

__all__ = [
    "MCPManager",
    "LangChainMCPClient",
    "MCPCrawlerAdapter",
    "create_mcp_crawler_adapter",
]
