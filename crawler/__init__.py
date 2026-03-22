"""
Crawler 模块 - 仅通过 MCP 调用
"""
from .data_cleaner import DataCleaner
from .mcp_wrapper import MCPCrawlerWrapper, create_mcp_crawler

__all__ = [
    "DataCleaner",
    "MCPCrawlerWrapper",
    "create_mcp_crawler",
]
