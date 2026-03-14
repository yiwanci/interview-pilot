"""
数据清洗
去重、过滤、结构化提取
"""
import re
import hashlib
from typing import Optional
from openai import OpenAI

from config import get_llm_config
from storage import RawDocument


class DataCleaner:
    """
    数据清洗器
    
    功能：
    - 去除广告、无关内容
    - 文本规范化
    - 去重
    - LLM 辅助结构化提取
    
    使用示例:
        cleaner = DataCleaner()
        cleaned_doc = cleaner.clean(raw_doc)
        qa_pairs = cleaner.extract_qa_pairs(text)
    """
    
    # 广告关键词
    AD_KEYWORDS = [
        "私信", "加微", "加v", "vx:", "wx:", "微信:",
        "点击链接", "优惠", "折扣", "免费领", "限时",
        "关注我", "求关注", "互粉", "点赞",
    ]
    
    # 最小内容长度
    MIN_CONTENT_LENGTH = 50
    
    def __init__(self):
        config = get_llm_config()
        self.llm_client = OpenAI(
            api_key=config["api_key"],
            base_url=config["base_url"],
        )
        self.llm_model = config["model"]
        
        # 去重用的哈希集合
        self._seen_hashes = set()
    
    def clean(self, doc: RawDocument) -> Optional[RawDocument]:
        """
        清洗单个文档
        
        Returns:
            清洗后的文档，如果应该过滤则返回 None
        """
        content = doc.content
        
        # 1. 基础清洗
        content = self._basic_clean(content)
        
        # 2. 检查是否是广告
        if self._is_ad(content):
            return None
        
        # 3. 检查长度
        if len(content) < self.MIN_CONTENT_LENGTH:
            return None
        
        # 4. 去重
        content_hash = self._get_hash(content)
        if content_hash in self._seen_hashes:
            return None
        self._seen_hashes.add(content_hash)
        
        # 5. 更新文档
        doc.content = content
        return doc
    
    def clean_batch(self, docs: list[RawDocument]) -> list[RawDocument]:
        """批量清洗"""
        cleaned = []
        for doc in docs:
            result = self.clean(doc)
            if result:
                cleaned.append(result)
        return cleaned
    
    def _basic_clean(self, text: str) -> str:
        """基础文本清洗"""
        # 去除多余空白
        text = re.sub(r'\s+', ' ', text)
        
        # 去除特殊字符
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', text)
        
        # 去除表情符号（保留中文、英文、数字、常用标点）
        text = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9\s.,!?;:，。！？；：、""''（）\[\]【】\-+*/=<>@#$%^&()_]', '', text)
        
        # 去除 URL
        text = re.sub(r'https?://\S+', '', text)
        
        # 去除 @用户
        text = re.sub(r'@\S+', '', text)
        
        # 去除话题标签
        text = re.sub(r'#\S+#?', '', text)
        
        return text.strip()
    
    def _is_ad(self, text: str) -> bool:
        """检查是否是广告"""
        text_lower = text.lower()
        
        # 关键词检测
        ad_count = sum(1 for kw in self.AD_KEYWORDS if kw in text_lower)
        if ad_count >= 2:
            return True
        
        # 联系方式检测
        if re.search(r'\d{5,}', text):  # 长数字串（可能是微信号、QQ）
            contact_patterns = ['加', '私', 'v', 'q', '微', '联系']
            if any(p in text_lower for p in contact_patterns):
                return True
        
        return False
    
    def _get_hash(self, text: str) -> str:
        """获取文本哈希（用于去重）"""
        # 简单预处理后哈希
        normalized = re.sub(r'\s+', '', text.lower())
        return hashlib.md5(normalized.encode()).hexdigest()
    
    def extract_qa_pairs(self, text: str) -> list[dict]:
        """
        用 LLM 提取 Q&A 对
        
        Args:
            text: 面经文本
        
        Returns:
            [{"question": "...", "answer": "...", "tags": [...]}]
        """
        prompt = f"""请从以下面经内容中提取面试问题和回答。

要求：
1. 每个问题单独提取
2. 如果没有明确回答，answer 填"未提供"
3. 推断问题所属的技术领域（tags）
4. 只提取技术相关问题，忽略闲聊

面经内容：
{text[:3000]}

返回 JSON 数组格式：
[
  {{"question": "问题1", "answer": "回答1", "tags": ["标签1", "标签2"]}},
  {{"question": "问题2", "answer": "回答2", "tags": ["标签1"]}}
]

请直接返回 JSON，不要其他内容："""

        try:
            response = self.llm_client.chat.completions.create(
                model=self.llm_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # 清理 markdown
            result_text = re.sub(r'^```json\s*', '', result_text)
            result_text = re.sub(r'\s*```$', '', result_text)
            
            import json
            return json.loads(result_text)
        
        except Exception as e:
            print(f"QA提取失败: {e}")
            return []
    
    def extract_key_points(self, text: str) -> list[str]:
        """
        提取关键知识点
        
        Args:
            text: 技术文本
        
        Returns:
            知识点列表
        """
        prompt = f"""请从以下技术内容中提取关键知识点。

要求：
1. 每个知识点用简短的短语表示
2. 只提取技术相关的知识点
3. 返回 JSON 数组

内容：
{text[:2000]}

返回格式：["知识点1", "知识点2", "知识点3"]

请直接返回 JSON 数组："""

        try:
            response = self.llm_client.chat.completions.create(
                model=self.llm_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
            )
            
            result_text = response.choices[0].message.content.strip()
            result_text = re.sub(r'^```json\s*', '', result_text)
            result_text = re.sub(r'\s*```$', '', result_text)
            
            import json
            return json.loads(result_text)
        
        except Exception as e:
            print(f"知识点提取失败: {e}")
            return []
    
    def classify_content(self, text: str) -> dict:
        """
        分类内容
        
        Returns:
            {"domain": "...", "category": "...", "tags": [...]}
        """
        prompt = f"""请对以下技术内容进行分类。

领域选项：java_backend, ai_agent, llm_algorithm, cs_basic
分类选项：
- java_backend: java_basic, spring, database, middleware, system_design
- ai_agent: llm_basic, rag, agent_framework, memory, tool_use
- llm_algorithm: transformer, training, inference, fine_tuning
- cs_basic: algorithm, os, network

内容：
{text[:1000]}

返回 JSON 格式：
{{"domain": "领域", "category": "分类", "tags": ["标签1", "标签2"]}}

请直接返回 JSON："""

        try:
            response = self.llm_client.chat.completions.create(
                model=self.llm_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
            )
            
            result_text = response.choices[0].message.content.strip()
            result_text = re.sub(r'^```json\s*', '', result_text)
            result_text = re.sub(r'\s*```$', '', result_text)
            
            import json
            return json.loads(result_text)
        
        except Exception as e:
            print(f"分类失败: {e}")
            return {"domain": "cs_basic", "category": "general", "tags": []}
    
    def reset_dedup(self):
        """重置去重缓存"""
        self._seen_hashes.clear()
