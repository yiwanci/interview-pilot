"""
自适应分块策略
根据文档类型采用不同的分块方式
"""
import re
import uuid
from typing import Optional
from openai import OpenAI

from config import get_llm_config
from storage import RawDocument, DocumentChunk


class AdaptiveChunker:
    """
    自适应分块器
    
    策略：
    - 面经类：LLM 提取 Q&A 对
    - 八股文：语义分块
    - 通用：固定长度分块
    
    使用示例:
        chunker = AdaptiveChunker()
        chunks = chunker.chunk(raw_document)
    """
    
    # 分块参数
    DEFAULT_CHUNK_SIZE = 500
    DEFAULT_OVERLAP = 50
    
    def __init__(self):
        config = get_llm_config()
        self.llm_client = OpenAI(
            api_key=config["api_key"],
            base_url=config["base_url"],
        )
        self.llm_model = config["model"]
    
    def chunk(self, doc: RawDocument) -> list[DocumentChunk]:
        """
        根据文档类型自动选择分块策略
        """
        source = doc.source.lower()
        
        if source in ["xiaohongshu", "douyin"]:
            # 面经类：提取 Q&A
            return self._chunk_interview(doc)
        elif source == "leetcode":
            # 算法题：整题为一个 chunk
            return self._chunk_leetcode(doc)
        else:
            # 通用：固定长度
            return self._chunk_fixed(doc)
    
    def _chunk_interview(self, doc: RawDocument) -> list[DocumentChunk]:
        """
        面经分块：LLM 提取 Q&A 对
        """
        qa_pairs = self._extract_qa_pairs(doc.content)
        
        if not qa_pairs:
            # 提取失败，回退到固定分块
            return self._chunk_fixed(doc)
        
        chunks = []
        for qa in qa_pairs:
            chunk = DocumentChunk(
                id=str(uuid.uuid4()),
                doc_id=doc.id,
                content=f"问题：{qa['question']}\n回答：{qa['answer']}",
                chunk_type="qa",
                source=doc.source,
                question=qa["question"],
                answer=qa["answer"],
                company=qa.get("company", doc.metadata.get("company", "")),
                position=qa.get("position", doc.metadata.get("position", "")),
                domain=self._infer_domain(qa["question"]),
                category=self._infer_category(qa["question"]),
                tags=qa.get("tags", []),
            )
            chunks.append(chunk)
        
        return chunks
    
    def _extract_qa_pairs(self, text: str) -> list[dict]:
        """
        用 LLM 提取 Q&A 对
        """
        prompt = f"""请从以下面经内容中提取面试问题和回答。

要求：
1. 每个问题单独提取
2. 如果没有明确回答，answer 填"未提供"
3. 推断问题所属的技术领域（tags）
4. 返回 JSON 数组格式

面经内容：
{text}

返回格式示例：
[
  {{"question": "HashMap底层原理", "answer": "数组+链表+红黑树...", "tags": ["Java", "集合框架"]}},
  {{"question": "Redis持久化", "answer": "RDB和AOF两种方式...", "tags": ["Redis", "数据库"]}}
]

请直接返回 JSON 数组，不要其他内容："""

        try:
            response = self.llm_client.chat.completions.create(
                model=self.llm_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # 清理可能的 markdown 标记
            result_text = re.sub(r'^```json\s*', '', result_text)
            result_text = re.sub(r'\s*```$', '', result_text)
            
            import json
            return json.loads(result_text)
        
        except Exception as e:
            print(f"QA提取失败: {e}")
            return []
    
    def _chunk_leetcode(self, doc: RawDocument) -> list[DocumentChunk]:
        """
        LeetCode 分块：整题为一个 chunk
        """
        chunk = DocumentChunk(
            id=str(uuid.uuid4()),
            doc_id=doc.id,
            content=doc.content,
            chunk_type="algorithm",
            source=doc.source,
            domain="cs_basic",
            category="algorithm",
            tags=doc.metadata.get("tags", []),
        )
        return [chunk]
    
    def _chunk_fixed(
        self,
        doc: RawDocument,
        chunk_size: int = None,
        overlap: int = None,
    ) -> list[DocumentChunk]:
        """
        固定长度分块
        """
        chunk_size = chunk_size or self.DEFAULT_CHUNK_SIZE
        overlap = overlap or self.DEFAULT_OVERLAP
        
        text = doc.content
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            chunk_text = text[start:end]
            
            # 尝试在句子边界切分
            if end < len(text):
                last_period = max(
                    chunk_text.rfind('。'),
                    chunk_text.rfind('！'),
                    chunk_text.rfind('？'),
                    chunk_text.rfind('\n'),
                )
                if last_period > chunk_size * 0.5:
                    chunk_text = chunk_text[:last_period + 1]
                    end = start + last_period + 1
            
            chunk = DocumentChunk(
                id=str(uuid.uuid4()),
                doc_id=doc.id,
                content=chunk_text.strip(),
                chunk_type="text",
                source=doc.source,
                domain=self._infer_domain(chunk_text),
            )
            chunks.append(chunk)
            
            start = end - overlap
        
        return chunks
    
    def _infer_domain(self, text: str) -> str:
        """推断领域"""
        text_lower = text.lower()
        
        # Java 后端关键词
        java_keywords = ["java", "spring", "jvm", "mybatis", "mysql", "redis", "kafka", "dubbo", "微服务"]
        if any(kw in text_lower for kw in java_keywords):
            return "java_backend"
        
        # AI Agent 关键词
        agent_keywords = ["agent", "langchain", "rag", "embedding", "向量", "prompt", "llm", "大模型"]
        if any(kw in text_lower for kw in agent_keywords):
            return "ai_agent"
        
        # 大模型算法关键词
        llm_keywords = ["transformer", "attention", "微调", "lora", "rlhf", "sft", "预训练"]
        if any(kw in text_lower for kw in llm_keywords):
            return "llm_algorithm"
        
        return "cs_basic"
    
    def _infer_category(self, text: str) -> str:
        """推断分类"""
        text_lower = text.lower()
        
        category_keywords = {
            "java_basic": ["集合", "多线程", "并发", "jvm", "gc", "反射", "hashmap", "arraylist", "线程池"],
            "spring": ["spring", "ioc", "aop", "boot", "cloud", "mybatis"],
            "database": ["mysql", "索引", "事务", "redis", "mongodb", "数据库"],
            "middleware": ["kafka", "mq", "nginx", "dubbo", "zookeeper"],
            "algorithm": ["排序", "搜索", "动态规划", "dp", "二叉树", "链表", "算法"],
            "network": ["tcp", "http", "https", "网络", "socket", "udp"],
            "rag": ["rag", "检索", "embedding", "向量"],
            "transformer": ["transformer", "attention", "注意力"],
        }
        
        for category, keywords in category_keywords.items():
            if any(kw in text_lower for kw in keywords):
                return category
        
        return "general"

