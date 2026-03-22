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
    
    # 最小内容长度（降低门槛）
    MIN_CONTENT_LENGTH = 20
    
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
        text = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9\s.,!?;:\u3002\u201c\u201d\u3001\uff01\uff08\uff0c\uff1a\uff1b\uff1c-\uff1f""''\u3010\u3011\u3014\u3015\u3016\u3017\u3018\u3019\u301a\u301b\u301c\u301d\u301e\u301f\u5b57\u5b58\u5b59\u5b60\u5b61\u5b62\u5b63\u2014\u2018\u2026\u202d\u2030\u2039\u3008\u300a\u300b\u300c\u300d\u300e\u300f\u3010\u3011\u3012\u3013\u301c\u301d\u301e\u301f\ufb01\ufb02\ufb03\ufb04\ufb05\ufb06\ufb07\ufe0f\ufe0b\ufe0c\ufe0d\ufe0e\ufe0f\ufe1a\ufe1b\ufe1c\ufe1d\ufe1e\ufe1f\ufe20\ufe21\ufe22\ufe23\ufe24\ufe25\ufe26\ufe27\ufe28\ufe29\ufe2a\ufe2b\ufe2c\ufe2d\ufe2e\ufe2f\ufe30\ufe31\ufe32\ufe33\ufe34\ufe35\ufe36\ufe37\ufe38\ufe39\ufe3a\ufe3b\ufe3c\ufe3d\ufe3e\ufe3f\ufe40\ufe41\ufe42\ufe43\ufe44\ufe45\ufe46\ufe47\ufe48\ufe49\ufe4a\ufe4b\ufe4c\ufe4d\ufe4e\ufe4f\ufe50\ufe51\ufe52\ufe53\ufe54\ufe55\ufe56\ufe57\ufe58\ufe59\ufe5a\ufe5b\ufe5c\ufe5d\ufe5e\ufe5f\ufe60\ufe61\ufe62\ufe63\ufe64\ufe65\ufe66\ufe67\ufe68\ufe69\ufe6a\ufe6b\ufe6c\ufe6d\ufe6e\ufe6f\ufe70\ufe71\ufe72\ufe73\ufe74\ufe75\ufe76\ufe77\ufe78\ufe79\ufe7a\ufe7b\ufe7c\ufe7d\ufe7e\ufe7f\ufe80\ufe81\ufe82\ufe83\ufe84\ufe85\ufe86\ufe87\ufe88\ufe89\ufe8a\ufe8b\ufe8c\ufe8d\ufe8e\ufe8f\ufe90\ufe91\ufe92\ufe93\ufe94\ufe95\ufe96\ufe97\ufe98\ufe99\ufe9a\ufe9b\ufe9c\ufe9d\ufe9e\ufe9f\uff01\uff02\uff03\uff04\uff05\uff06\uff07\uff08\uff09\uff0a\uff0b\uff0c\uff0d\uff0e\uff0f\uff10\uff11\uff12\uff13\uff14\uff15\uff16\uff17\uff18\uff19\uff1a\uff1b\uff1c\uff1d\uff1e\uff1f\uff20\uff21\uff22\uff23\uff24\uff25\uff26\uff27\uff28\uff29\uff2a\uff2b\uff2c\uff2d\uff2e\uff2f\uff30\uff31\uff32\uff33\uff34\uff35\uff36\uff37\uff38\uff39\uff3a\uff3b\uff3c\uff3d\uff3e\uff3f\uff40\uff41\uff42\uff43\uff44\uff45\uff46\uff47\uff48\uff49\uff4a\uff4b\uff4c\uff4d\uff4e\uff4f\uff50\uff51\uff52\uff53\uff54\uff55\uff56\uff57\uff58\uff59\uff5a\uff5b\uff5c\uff5d\uff5e\uff5f\uff60\uff61\uff62\uff63\uff64\uff65\uff66\uff67\uff68\uff69\uff6a\uff6b\uff6c\uff6d\uff6e\uff6f\uff70\uff71\uff72\uff73\uff74\uff75\uff76\uff77\uff78\uff79\uff7a\uff7b\uff7c\uff7d\uff7e\uff7f\uff80\uff81\uff82\uff83\uff84\uff85\uff86\uff87\uff88\uff89\uff8a\uff8b\uff8c\uff8d\uff8e\uff8f\uff90\uff91\uff92\uff93\uff94\uff95\uff96\uff97\uff98\uff99\uff9a\uff9b\uff9c\uff9d\uff9e\uff9f\uffa0\uffa1\uffa2\uffa3\uffa4\uffa5\uffa6\uffa7\uffa8\uffa9\uffaa\uffab\uffff\ufe0f\ufe0b\ufe0c\ufe0d\ufe0e\ufe0f\ufe1a\ufe1b\ufe1c\ufe1d\ufe1e\ufe1f\ufe20\ufe21\ufe22\ufe23\ufe24\ufe25\ufe26\ufe27\ufe28\ufe29\ufe2a\ufe2b\ufe2c\ufe2d\ufe2e\ufe2f\ufe30\ufe31\ufe32\ufe33\ufe34\ufe35\ufe36\ufe37\ufe38\ufe39\ufe3a\ufe3b\ufe3c\ufe3d\ufe3e\ufe3f\ufe40\ufe41\ufe42\ufe43\ufe44\ufe45\ufe46\ufe47\ufe48\ufe49\ufe4a\ufe4b\ufe4c\ufe4d\ufe4e\ufe4f\ufe50\ufe51\ufe52\ufe53\ufe54\ufe55\ufe56\ufe57\ufe58\ufe59\ufe5a\ufe5b\ufe5c\ufe5d\ufe5e\ufe5f\ufe60\ufe61\ufe62\ufe63\ufe64\ufe65\ufe66\ufe67\ufe68\ufe69\ufe6a\ufe6b\ufe6c\ufe6d\ufe6e\ufe6f\ufe70\ufe71\ufe72\ufe73\ufe74\ufe75\ufe76\ufe77\ufe78\ufe79\ufe7a\ufe7b\ufe7c\ufe7d\ufe7e\ufe7f\ufe80\ufe81\ufe82\ufe83\ufe84\ufe85\ufe86\ufe87\ufe88\ufe89\ufe8a\ufe8b\ufe8c\ufe8d\ufe8e\ufe8f\ufe90\ufe91\ufe92\ufe93\ufe94\ufe95\ufe96\ufe97\ufe98\ufe99\ufe9a\ufe9b\ufe9c\ufe9d\ufe9e\ufe9f\uff01\uff02\uff03\uff04\uff05\uff06\uff07\uff08\uff09\uff0a\uff0b\uff0c\uff0d\uff0e\uff0f\uff10\uff11\uff12\uff13\uff14\uff15\uff16\uff17\uff18\uff19\uff1a\uff1b\uff1c\uff1d\uff1e\uff1f\uff20\uff21\uff22\uff23\uff24\uff25\uff26\uff27\uff28\uff29\uff2a\uff2b\uff2c\uff2d\uff2e\uff2f\uff30\uff31\uff32\uff33\uff34\uff35\uff36\uff37\uff38\uff39\uff3a\uff3b\uff3c\uff3d\uff3e\uff3f\uff40\uff41\uff42\uff43\uff44\uff45\uff46\uff47\uff48\uff49\uff4a\uff4b\uff4c\uff4d\uff4e\uff4f\uff50\uff51\uff52\uff53\uff54\uff55\uff56\uff57\uff58\uff59\uff5a\uff5b\uff5c\uff5d\uff5e\uff5f\uff60\uff61\uff62\uff63\uff64\uff65\uff66\uff67\uff68\uff69\uff6a\uff5b\uff6c\uff6d\uff6e\uff6f\uff70\uff71\uff72\uff73\uff74\uff75\uff76\uff77\uff78\uff79\uff7a\uff7b\uff7c\uff7d\uff7e\uff7f\uff80\uff81\uff82\uff83\uff84\uff85\uff86\uff87\uff88\uff89\uff8a\uff8b\uff8c\uff8d\uff8e\uff8f\uff90\uff91\uff92\uff93\uff94\uff95\uff96\uff97\uff98\uff99\uff9a\uff9b\uff9c\uff9d\uff9e\uff9f\uffa0\uffa1\uffa2\uffa3\uffa4\uffa5\uffa6\uffa7\uffa8\uffa9\uffaa\uffab\uffef\u200b\u200c\u200d\u200e\u200f\u2010\u2011\u2012\u2013\u2014\u2015\u2016\u2017\u2018\u2019\u201a\u201b\u201c\u201d\u201e\u201f\u2020\u2021\u2022\u2023\u2024\u2025\u2026\u2027\u2028\u2029\u202a\u202b\u202c\u202d\u202e\u202f\u2030\u2031\u2032\u2033\u2034\u2035\u2036\u2037\u2038\u2039\u203a\u203b\u203c\u203d\u203e\u203f\u2040\u2041\u2042\u2043\u2044\u2045\u2046\u2047\u2048\u2049\u204a\u204b\u204c\u204d\u204e\u204f\u2050\u2051\u2052\u2053\u2054\u2055\u2056\u2057\u2058\u2059\u205a\u205b\u205c\u205d\u205e\u205f\u2060\u2061\u2062\u2063\u2064\u2065\u2066\u2067\u2068\u2069\u206a\u206b\u206c\u206d\u206e\u206f\u2070\u2071\u2072\u2073\u2074\u2075\u2076\u2077\u2078\u2079\u207a\u207b\u207c\u207d\u207e\u207f\u2080\u2081\u2082\u2083\u2084\u2085\u2086\u2087\u2088\u2089\u208a\u208b\u208c\u208d\u208e\u208f\u2090\u2091\u2092\u2093\u2094\u2095\u2096\u2097\u2098\u2099\u209a\u209b\u209c\u209d\u209e\u209f\u20a0\u20a1\u20a2\u20a3\u20a4\u20a5\u20a6\u20a7\u20a8\u20a9\u20aa\u20ab\u20ac\u20ad\u20ae\u20af\u20b0\u20b1\u20b2\u20b3\u20b4\u20b5\u20b6\u20b7\u20b8\u20b9\u20ba\u20bb\u20bc\u20bd\u20be\u20bf\u20c0\u20c1\u20c2\u20c3\u20c4\u20c5\u20c6\u20c7\u20c8\u20c9\u20ca\u20cb\u20cc\u20cd\u20ce\u20cf\u20d0\u20d1\u20d2\u20d3\u20d4\u20d5\u20d6\u20d7\u20d8\u20d9\u20da\u20db\u20dc\u20dd\u20de\u20df\u20e0\u20e1\u20e2\u20e3\u20e4\u20e5\u20e6\u20e7\u20e8\u20e9\u20ea\u20eb\u20ec\u20ed\u20ee\u20ef\-\+*/=<>@#$%^&()_]', '', text)
        
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
