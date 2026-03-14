"""
爬虫采集节点
"""
import re
import json
from openai import OpenAI

from config import get_llm_config
from crawler import XiaohongshuCrawler, DouyinCrawler, LeetCodeCrawler, DataCleaner
from rag import RAGPipeline
from agent.state import AgentState


class CrawlerNode:
    """爬虫采集节点"""
    
    def __init__(self):
        config = get_llm_config()
        self.llm_client = OpenAI(
            api_key=config["api_key"],
            base_url=config["base_url"],
        )
        self.llm_model = config["model"]
        self.rag = RAGPipeline()
        self.cleaner = DataCleaner()
        
        self.crawlers = {
            "xiaohongshu": XiaohongshuCrawler(),
            "douyin": DouyinCrawler(),
            "leetcode": LeetCodeCrawler(),
        }
    
    def _get_parse_prompt(self, user_input: str) -> str:
        """获取解析 prompt（避免 f-string 转义问题）"""
        return f'''请解析用户的数据采集需求。

用户输入：{user_input}

请提取：
1. 数据来源（xiaohongshu/douyin/leetcode/manual）
2. 搜索关键词
3. 数量限制（默认20）

返回 JSON 格式，示例：
{{"source": "xiaohongshu", "keyword": "Java面经", "limit": 20}}

请直接返回 JSON：'''
    
    def __call__(self, state: AgentState) -> AgentState:
        """爬虫节点处理"""
        user_input = state.get("user_input", "")
        
        try:
            # 1. 解析采集需求
            crawl_params = self._parse_crawl_request(user_input)
            state["crawl_keyword"] = crawl_params.get("keyword", "")
            state["crawl_source"] = crawl_params.get("source", "")
            
            source = crawl_params.get("source", "")
            keyword = crawl_params.get("keyword", "")
            limit = crawl_params.get("limit", 20)
            
            # 2. 检查是否是手动导入
            if source == "manual" or "导入" in user_input:
                state["response"] = self._manual_import_guide()
                return state
            
            # 3. 检查爬虫是否可用
            if source not in self.crawlers:
                state["response"] = f"暂不支持 {source} 来源，目前支持：小红书、抖音、LeetCode"
                return state
            
            # 4. 执行爬取
            crawler = self.crawlers[source]
            
            if source == "leetcode" and self._is_company_query(keyword):
                docs = crawler.get_by_company(keyword, limit=limit)
            else:
                docs = crawler.search(keyword, limit=limit)
            
            # 5. 检查结果
            if not docs:
                state["response"] = self._no_result_response(source)
                return state
            
            # 6. 清洗数据
            cleaned_docs = self.cleaner.clean_batch(docs)
            
            # 7. 入库
            total_chunks = 0
            for doc in cleaned_docs:
                chunk_ids = self.rag.ingest(doc)
                total_chunks += len(chunk_ids)
            
            # 8. 生成报告
            state["response"] = self._generate_report(
                source=source,
                keyword=keyword,
                raw_count=len(docs),
                cleaned_count=len(cleaned_docs),
                chunk_count=total_chunks,
            )
        
        except Exception as e:
            state["error"] = str(e)
            state["response"] = f"采集过程出错：{e}"
        
        return state
    
    def _parse_crawl_request(self, user_input: str) -> dict:
        """解析采集请求"""
        result = self._quick_parse(user_input)
        if result:
            return result
        
        try:
            response = self.llm_client.chat.completions.create(
                model=self.llm_model,
                messages=[{
                    "role": "user",
                    "content": self._get_parse_prompt(user_input)
                }],
                temperature=0.1,
            )
            
            result_text = response.choices[0].message.content.strip()
            result_text = re.sub(r'^```json\s*', '', result_text)
            result_text = re.sub(r'\s*```$', '', result_text)
            
            return json.loads(result_text)
        
        except Exception:
            return {"source": "manual", "keyword": "", "limit": 20}
    
    def _quick_parse(self, text: str) -> dict:
        """快速规则解析"""
        text_lower = text.lower()
        
        source = ""
        if "小红书" in text or "xhs" in text_lower:
            source = "xiaohongshu"
        elif "抖音" in text or "douyin" in text_lower:
            source = "douyin"
        elif "leetcode" in text_lower or "力扣" in text:
            source = "leetcode"
        
        if not source:
            return None
        
        # 简单提取关键词
        keyword = text
        for word in ["小红书", "抖音", "leetcode", "力扣", "搜集", "抓取", "爬取", "面经", "的", "上"]:
            keyword = keyword.replace(word, "")
        keyword = keyword.strip()
        
        return {"source": source, "keyword": keyword or "面经", "limit": 20}
    
    def _is_company_query(self, keyword: str) -> bool:
        """判断是否是公司查询"""
        companies = ["bytedance", "字节", "alibaba", "阿里", "tencent", "腾讯", "meituan", "美团"]
        return any(c in keyword.lower() for c in companies)
    
    def _no_result_response(self, source: str) -> str:
        """无结果响应"""
        if source in ["xiaohongshu", "douyin"]:
            return f"{source} 需要登录Cookie，建议使用 MediaCrawler 工具或手动导入。"
        return "未找到相关内容，请尝试其他关键词。"
    
    def _manual_import_guide(self) -> str:
        """手动导入指南"""
        return """📥 手动导入指南

1. 直接粘贴面经内容到对话框
2. 或将 JSON 文件放到 data/raw/ 目录后输入「导入文件 xxx.json」

MediaCrawler 工具：https://github.com/NanmiCoder/MediaCrawler"""
    
    def _generate_report(self, source: str, keyword: str, raw_count: int, cleaned_count: int, chunk_count: int) -> str:
        """生成采集报告"""
        source_name = {"xiaohongshu": "小红书", "douyin": "抖音", "leetcode": "LeetCode"}.get(source, source)
        return f"""✅ 采集完成！

来源：{source_name}
关键词：{keyword}
原始：{raw_count} 条 → 清洗后：{cleaned_count} 条 → 分块：{chunk_count} 个

输入「考考我」开始练习，或继续采集其他内容。"""


def crawler_node(state: AgentState) -> AgentState:
    """函数式调用"""
    node = CrawlerNode()
    return node(state)
