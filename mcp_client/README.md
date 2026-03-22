# MCP 集成指南

## 概述

本项目已集成 MCP (Model Context Protocol) 支持，通过 MCP 服务器端可以轻松扩展爬虫和其他工具能力。

## 技术栈

- **MCP SDK**: `langchain-mcp-adapters`
- **连接方式**: HTTP (`streamable_http`)

## 架构

```
mcp/
├── __init__.py           # 模块导出
├── langchain_client.py    # LangChain MCP 客户端
├── manager.py            # MCP 连接管理器（单例）
├── adapters.py           # 工具适配器（转换为项目接口）
└── README.md             # 本文档
```

## 快速开始

### 1. 安装依赖

```bash
pip install langchain-mcp-adapters>=0.1.0
```

### 2. 配置 MCP 服务器（`.env`）

```bash
# 启用小红书 MCP 服务器
MCP_XIAOHONGSHU_ENABLED=true
MCP_XIAOHONGSHU_URL=http://localhost:18060/mcp

# 启用抖音 MCP 服务器（示例）
# MCP_DOUYIN_ENABLED=true
# MCP_DOUYIN_URL=http://localhost:18061/mcp
```

### 3. 启动 MCP 服务器

在另一个终端运行你的 MCP 服务器：

```bash
# 例如：小红书 MCP 服务器
python xiaohongshu_mcp_server.py

# 或使用已启动的服务（如 Docker）
```

### 4. 启动项目

```bash
python -m streamlit run ui/app.py
```

启动后会看到：

```
[MCP] 已连接，可用工具：5
[MCP] 初始化完成，已连接 1 个服务器，工具：5
[CrawlerNode] MCP 爬虫已启用，支持来源：['xiaohongshu']
```

### 5. 使用

在对话框中输入：

```
爬取 小红书 Java面经
```

## 工作流程

```
用户输入 "爬取 小红书 Java面经"
    ↓
CrawlerNode 解析
    ├─ source: "xiaohongshu"
    └─ keyword: "Java面经"
    ↓
检查 MCP 是否可用
    ├─ 可用 → 调用 MCP 工具 "search_xiaohongshu"
    └─ 不可用 → 降级到本地爬虫
    ↓
MCP 返回数据（可能是 Markdown 或 JSON）
    ↓
转换为 RawDocument
    ↓
清洗数据 → 入库 → 返回报告
```

## 代码示例

### 使用适配器

```python
from mcp import MCPCrawlerAdapter

# 创建适配器（会自动连接 MCP）
adapter = MCPCrawlerAdapter()

if adapter.is_available():
    # 爬取数据
    docs = adapter.crawl(
        source="xiaohongshu",
        keyword="Redis面经",
        limit=20,
    )

    for doc in docs:
        print(f"{doc.title}")
        print(f"{doc.url}")
        print(f"{doc.content[:100]}...")
```

### 直接调用 MCP 工具

```python
from mcp import MCPManager

# 初始化管理器
manager = MCPManager()
manager.initialize_sync()

# 调用工具
if manager.is_available():
    result = manager.call_tool_sync(
        tool_name="search_xiaohongshu",
        arguments={
            "query": "Java面经",
            "limit": 10,
        },
    )
    print(result)
```

### 查看可用工具

```python
from mcp import MCPManager

manager = MCPManager()
manager.initialize_sync()

print("可用工具：")
for tool_name in manager.get_tool_names():
    print(f"  - {tool_name}")
```

## 降级策略

如果 MCP 不可用，系统会自动降级到本地爬虫：

```
MCP 爬虫失败/不可用
    ↓
尝试本地爬虫
    ├─ 小红书/抖音 → MediaCrawler
    └─ LeetCode → 本地爬虫
    ↓
仍失败 → 提示手动导入
```

## MCP 服务器示例

### 小红书 MCP 服务器（参考）

```python
from langchain_community.chat_models.tongyi import ChatTongyi
from langchain.agents import create_agent
from langchain_mcp_adapters.client import MultiServerMCPClient
from mcp.server import Server

server = Server("xiaohongshu")

@server.tool()
def search_xiaohongshu(query: str, limit: int = 10) -> str:
    """搜索小红书笔记，返回 Markdown 格式"""
    # 实际爬取逻辑...
    return markdown_content

if __name__ == "__main__":
    server.run()
```

### LangChain MCP 服务器（HTTP 模式）

```python
from langchain_mcp_adapters import create_mcp_client
from mcp.server import Server

server = Server("my-crawler")

@server.tool()
def crawl_web(url: str) -> dict:
    """爬取网页内容"""
    import httpx
    response = httpx.get(url)
    return {"content": response.text}

if __name__ == "__main__":
    # 创建 HTTP MCP 服务器
    create_mcp_client(server).run("0.0.0.0", 18060)
```

## 开发自定义 MCP 服务器

### 步骤 1：创建 MCP 服务器

创建文件 `my_mcp_server.py`：

```python
from mcp.server import Server
from langchain_mcp_adapters import create_mcp_client

server = Server("my-crawler")

@server.tool()
def search_github(keyword: str, limit: int = 10) -> list:
    """搜索 GitHub 仓库"""
    # 调用 GitHub API
    return [
        {
            "id": "1",
            "title": "仓库名称",
            "url": "https://github.com/...",
            "content": "描述内容",
        }
    ]

if __name__ == "__main__":
    # 启动 HTTP 服务器，监听 18060 端口
    create_mcp_client(server).run("0.0.0.0", 18060)
```

### 步骤 2：启动 MCP 服务器

```bash
python my_mcp_server.py
```

### 步骤 3：配置项目

在 `.env` 中添加：

```bash
MY_MCP_ENABLED=true
MY_MCP_URL=http://localhost:18060/mcp
```

### 步骤 4：更新 `mcp/manager.py`

在 `_load_configs()` 方法中添加：

```python
# GitHub MCP 服务器
if os.getenv("MY_MCP_ENABLED", "false").lower() == "true":
    url = os.getenv("MY_MCP_URL", "http://localhost:18060/mcp")
    configs.append(MCPServerConfig(
        name="my_crawler",
        transport="streamable_http",
        url=url,
        enabled=True,
    ))
```

### 步骤 5：使用

重启项目，在对话框输入：

```
爬取 github java 面经
```

## 调试

### 启用详细日志

```bash
# 查看 MCP 连接和工具调用日志
python -m streamlit run ui/app.py
```

### 测试 MCP 连接

```python
from mcp import MCPManager

manager = MCPManager()
manager.initialize_sync()

if manager.is_available():
    print("✅ MCP 连接成功")
    print(f"工具数量：{len(manager.get_all_tools())}")

    # 测试调用
    result = manager.call_tool_sync(
        tool_name="search_xiaohongshu",
        arguments={"query": "test", "limit": 1},
    )
    print(f"测试结果：{result}")
else:
    print("❌ MCP 连接失败")
```

## 常见问题

### Q: MCP 工具返回 Markdown 格式，怎么处理？

A: `MCPCrawlerAdapter` 会自动解析 Markdown，提取标题和内容为 `RawDocument`。如果格式特殊，可以在 `adapters.py` 中自定义解析逻辑。

### Q: 如何同时使用多个 MCP 服务器？

A: 在 `.env` 中配置多个服务器，`MCPManager` 会自动连接所有：

```bash
MCP_XIAOHONGSHU_ENABLED=true
MCP_XIAOHONGSHU_URL=http://localhost:18060/mcp

MCP_DOUYIN_ENABLED=true
MCP_DOUYIN_URL=http://localhost:18061/mcp
```

### Q: MCP 服务器启动失败怎么办？

A: 检查：
1. 端口是否被占用
2. MCP 服务器依赖是否安装
3. 网络连接是否正常

### Q: 如何禁用 MCP？

A: 在 `.env` 中设置 `MCP_XIAOHONGSHU_ENABLED=false`，项目会降级到本地爬虫。

## 下一步

- 为其他节点（`study_node`, `interview_node`）添加 MCP 支持
- 添加更多 MCP 服务器（GitHub、Web 爬虫等）
- 实现资源管理（通过 MCP 访问远程文件、数据库等）
