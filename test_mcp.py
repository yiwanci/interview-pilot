import asyncio
from langchain_community.chat_models import ChatTongyi
from langchain.agents import create_agent
from langchain_mcp_adapters.client import MultiServerMCPClient
from config import get_llm_config

async def main():
    # 获取 LLM 配置
    llm_config = get_llm_config()

    # 创建 MCP 客户端
    client = MultiServerMCPClient({
        "xiaohongshu": {
            "transport": "streamable_http",
            "url": "http://localhost:18060/mcp",
        }
    })

    # 获取工具
    tools = await client.get_tools()
    print(f"工具数量: {len(tools)}")
    print("工具列表:")
    for t in tools:
        print(f"  - {t.name}")

    # 创建模型
    model = ChatTongyi(
        model=llm_config["model"],
        api_key=llm_config["api_key"],
    )

    # 创建 Agent
    agent = create_agent(model, tools)

    # 测试调用
    result = await agent.ainvoke({
        "messages": [
            {
                "role": "user",
                "content": "搜索与Java面经相关的小红书笔记，返回前3条。把笔记内容输出为Markdown格式。要求把帖子的内容输出为Markdown格式。不要提其他无关的内容"
            }
        ]
    })

    print("\nAgent 响应:")
    for msg in result["messages"]:
        print(f"类型: {type(msg).__name__}")
        print(f"内容: {msg.content}")


if __name__ == "__main__":
    asyncio.run(main())
