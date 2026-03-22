"""
爬虫采集节点（仅通过 MCP）
"""
import json
import re
from pathlib import Path
import logging

# 配置日志系统
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

from crawler import DataCleaner, create_mcp_crawler
from rag import RAGPipeline
from agent.state import AgentState
from config.multimodal_config import get_multimodal_config, is_multimodal_available


class CrawlerNode:
    """爬虫采集节点（仅支持 MCP）"""

    def __init__(self):
        from openai import OpenAI
        from config import get_llm_config
        from config.multimodal_config import get_multimodal_config, is_multimodal_available

        # LLM 客户端（用于总结）- 使用多模态大模型
        if is_multimodal_available():
            logger.info("[CrawlerNode] 使用多模态大模型进行面经分析")
            multimodal_config = get_multimodal_config()
            self.llm_client = OpenAI(
                api_key=multimodal_config["api_key"],
                base_url=multimodal_config["base_url"],
            )
            self.llm_model = multimodal_config["model"]
        else:
            logger.info("[CrawlerNode] 使用标准LLM模型")
            llm_config = get_llm_config()
            self.llm_client = OpenAI(
                api_key=llm_config["api_key"],
                base_url=llm_config["base_url"],
            )
            self.llm_model = llm_config["model"]

        # RAG 管道
        try:
            self.rag = RAGPipeline()
            self.rag_available = self.rag.available
        except Exception as e:
            logger.warning(f"[CrawlerNode] RAG not available: {e}")
            self.rag = None
            self.rag_available = False

        # 数据清洗器
        self.cleaner = DataCleaner()

        # MCP 爬虫
        self.mcp_crawler = create_mcp_crawler()
        if self.mcp_crawler:
            sources = self.mcp_crawler.list_supported_sources()
            logger.info(f"[CrawlerNode] MCP 爬虫已启用，支持来源：{sources}")
        else:
            logger.warning("[CrawlerNode] MCPM 爬虫不可用，请检查配置")

    def __call__(self, state: AgentState) -> AgentState:
        """爬虫节点处理"""
        user_input = state.get("user_input", "")

        logger.info(f"[CrawlerNode] 处理请求: {user_input[:50]}...")

        try:
            # 检查 MCP 是否可用
            if not self.mcp_crawler:
                logger.warning("[CrawlerNode] MCP 爬虫不可用")
                state["response"] = self._mcp_unavailable_response()
                return state

            # 检查是否是文件导入请求
            if self._is_file_import_request(user_input):
                logger.info("[CrawlerNode] 识别为文件导入请求")
                return self._handle_file_import(user_input)

            if self._is_list_files_request(user_input):
                logger.info("[CrawlerNode] 识别为列出文件请求")
                return self._handle_list_files()

            if self._is_json_format_question(user_input):
                logger.info("[CrawlerNode] 识别为 JSON 格式询问")
                state["response"] = self._json_format_guide()
                return state

            # 直接传给 MCP Agent，返回内容给用户
            try:
                logger.info(f"[CrawlerNode] 直接调用 MCP Agent: {user_input[:50]}...")
                raw_content = self.mcp_crawler.crawl_direct(user_input)
                logger.info(f"[CrawlerNode] 爬取成功，内容长度: {len(raw_content)}")

                # 用 LLM 总结原始内容
                summary = self._summarize_content(user_input, raw_content)
                state["response"] = summary
                return state

            except Exception as e:
                logger.error(f"[CrawlerNode] 爬取失败: {e}", exc_info=True)
                state["response"] = self._crawl_error_response(str(e))
                return state

        except Exception as e:
            logger.error(f"[CrawlerNode] 处理异常: {e}", exc_info=True)
            state["error"] = str(e)
            state["response"] = f"采集过程出错：{e}"

        return state

    def _summarize_content(self, user_query: str, raw_content: str) -> str:
        """用 LLM 总结原始内容"""
        prompt = f"""用户请求：{user_query}

我通过爬虫获取了以下内容：

{raw_content}

请帮我整理这些内容，要求：
1. 完整提取所有面试题，不要省略
2. 如果内容包含图片引用，请描述图片中可能包含的面试题
3. 对于图片格式的面试题，提取并整理成文字描述
4. 按题目清晰列出，每题一个条目
5. 保留题目类型（选择题、问答题、代码题等）
6. 不要添加无关解释，只列出面试题

直接输出面试题列表："""

        try:
            response = self.llm_client.chat.completions.create(
                model=self.llm_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"[CrawlerNode] LLM 总结失败: {e}", exc_info=True)
            return f"爬取成功，但总结失败。\n\n{raw_content[:500]}..."

    def _mcp_unavailable_response(self) -> str:
        """MCP 不可用响应"""
        return """MCP 爬虫未配置！

**请按以下步骤配置：**

1. 安装依赖
   ```bash
   pip install langchain-mcp-adapters>=0.1.0
   ```

2. 启动 MCP 服务器
   在另一个终端运行你的 MCP 服务器（确保监听正确端口）

3. 配置环境变量（.env）
   ```bash
   MCP_XIAOHONGSHU_ENABLED=true
   MCP_XIAOHONGSHU_URL=http://localhost:18060/mcp

   # 或其他 MCP 服务器
   # MCP_DOUYIN_ENABLED=true
   # MCP_DOUYIN_URL=http://localhost:18061/mcp
   ```

4. 重启项目

配置完成后，即可使用 MCP 爬取数据！"""

    def _crawl_error_response(self, error: str) -> str:
        """爬取错误响应"""
        return f"""爬取失败

**错误信息：**
{error}

**建议：**
1. 检查 MCP 服务器是否正在运行
2. 检查 .env 中的 URL 配置是否正确
3. 确保小红书等平台已正确配置"""

    def _no_result_response(self) -> str:
        """无结果响应"""
        return """未找到相关内容

- 状态：搜索成功但无匹配结果

请尝试：
1. 使用不同的关键词
2. 检查关键词拼写
3. 或降低搜索范围"""

    def _json_format_guide(self) -> str:
        """JSON 格式指南"""
        return """可以直接用 JSON 数组文件，数组每个元素是一条面经，最少要有 `content` 字段。

推荐格式（xxx.json）：

```json
[
  {
    "title": "字节一面",
    "content": "面试问了 JVM、Redis、MySQL 索引...",
    "source": "xiaohongshu",
    "url": "https://example.com/post/1"
  },
  {
    "title": "美团后端面经",
    "content": "问了分布式事务、线程池参数、GC 调优...",
    "source": "manual"
  }
]
```

放到 `data/raw/` 后输入：`导入文件 xxx.json`。"""

    # ============ 文件导入 ============

    def _is_json_format_question(self, text: str) -> bool:
        """判断是否是 JSON 格式询问"""
        text_lower = text.lower()
        keywords = ["json格式", "json格式怎么写", "文件格式", "怎样导入", "如何导入", "格式说明"]
        return any(kw in text_lower for kw in keywords)

    def _is_file_import_request(self, text: str) -> bool:
        """判断是否是文件导入请求"""
        text_lower = text.lower()
        keywords = ["导入文件", "导入", "load file", "import file", "加载文件"]
        return any(kw in text_lower for kw in keywords)

    def _is_list_files_request(self, text: str) -> bool:
        """判断是否是列出文件请求"""
        text_lower = text.lower()
        keywords = ["列出文件", "查看文件", "有什么文件", "list files", "文件列表"]
        return any(kw in text_lower for kw in keywords)

    def _handle_list_files(self) -> AgentState:
        """处理列出文件请求"""
        state = AgentState()
        raw_dir = Path(__file__).parent.parent.parent / "data" / "raw"

        if not raw_dir.exists():
            raw_dir.mkdir(parents=True)

        files = list(raw_dir.glob("*.json")) + list(raw_dir.glob("*.jsonl"))

        if not files:
            state["response"] = """data/raw/ 目录中暂无文件。

请将面经 JSON 文件放到 data/raw/ 目录下，然后输入「导入文件 xxx.json」。"""
            return state

        file_list = "\n".join([f"  • {f.name}" for f in files[:10]])
        if len(files) > 10:
            file_list += f"\n  ... 还有 {len(files) - 10} 个文件"

        state["response"] = f"""找到以下文件：

{file_list}

请输入「导入文件 文件名.json」来导入，例如：
- 导入文件 xiaohongshu.json
- 导入文件 douyin_2024.json"""
        return state

    def _handle_file_import(self, user_input: str) -> AgentState:
        """处理文件导入请求"""
        state = AgentState()

        # 提取文件名
        file_name = self._extract_file_name(user_input)

        if not file_name:
            logger.warning("[CrawlerNode] 无法提取文件名")
            state["response"] = self._json_format_guide()
            return state

        # 文件路径
        raw_dir = Path(__file__).parent.parent.parent / "data" / "raw"
        file_path = raw_dir / file_name

        logger.info(f"[CrawlerNode] 导入文件: {file_path}")

        try:
            # 加载文件
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            logger.info("[CrawlerNode] 文件加载成功")

            # 统一为数组
            if isinstance(data, dict):
                data = [data]

            # 转换为 RawDocument
            from storage import RawDocument
            docs = []
            for item in data:
                if isinstance(item, dict):
                    doc = RawDocument(
                        id=item.get("id", ""),
                        source=item.get("source", "manual"),
                        url=item.get("url", ""),
                        title=item.get("title", ""),
                        content=item.get("content", ""),
                        author=item.get("author", ""),
                        likes=item.get("likes", 0),
                        metadata=item.get("metadata", {}),
                    )
                    if doc.content:
                        docs.append(doc)

            logger.info(f"[CrawlerNode] 解析文档: {len(docs)} 条")

            if not docs:
                logger.warning("[CrawlerNode] 文件无有效数据")
                state["response"] = f"文件 `{file_name}` 中没有找到有效数据，请检查文件格式。"
                return state

            # 清洗数据
            cleaned_docs = self.cleaner.clean_batch(docs)
            logger.info(f"[CrawlerNode] 清洗完成: {len(cleaned_docs)} 条")

            # 入库
            total_chunks = 0
            if self.rag_available and self.rag:
                logger.info("[CrawlerNode] 开始入库")
                for doc in cleaned_docs:
                    try:
                        chunk_ids = self.rag.ingest(doc)
                        total_chunks += len(chunk_ids)
                    except Exception as e:
                        logger.warning(f"[CrawlerNode] 入库失败: {e}")
                logger.info(f"[CrawlerNode] 入库完成: {total_chunks} 个分块")

            # 生成报告
            logger.info(f"[CrawlerNode] 导入成功: {file_name}, chunks={total_chunks}")
            state["response"] = f"""文件导入成功！

文件：{file_name}
原始：{len(docs)} 条 → 清洗后：{len(cleaned_docs)} 条 → 分块：{total_chunks} 个

输入「考考我」开始练习，或继续导入其他文件。"""

        except FileNotFoundError:
            logger.error(f"[CrawlerNode] 文件不存在: {file_name}")
            state["response"] = f"找不到文件 `{file_name}`。请先将文件放到 data/raw/ 目录下，然后输入「列出文件」查看可用文件。"
        except json.JSONDecodeError:
            logger.error(f"[CrawlerNode] JSON 解析失败: {file_name}")
            state["response"] = f"文件 `{file_name}` 不是有效的 JSON 格式，请检查文件内容。"
        except Exception as e:
            logger.error(f"[CrawlerNode] 导入异常: {e}", exc_info=True)
            state["error"] = str(e)
            state["response"] = f"导入文件时出错：{e}"

        return state

    def _extract_file_name(self, text: str) -> str:
        """从输入中提取文件名"""
        patterns = [
            r'导入文件\s+([^\s]+\.(?:json|jsonl))',
            r'导入\s+([^\s]+\.(?:json|jsonl))',
            r'load file\s+([^\s]+\.(?:json|jsonl))',
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()

        if ".json" in text:
            words = text.split()
            for word in words:
                if word.endswith(".json") or word.endswith(".jsonl"):
                    return word

        return ""

    def _generate_report(self, raw_count: int, cleaned_count: int, chunk_count: int) -> str:
        """生成采集报告"""
        return f"""采集完成！

原始：{raw_count} 条 → 清洗后：{cleaned_count} 条 → 分块：{chunk_count} 个

输入「考考我」开始练习，或继续采集其他内容。"""


def crawler_node(state: AgentState) -> AgentState:
    """函数式调用"""
    node = CrawlerNode()
    return node(state)
