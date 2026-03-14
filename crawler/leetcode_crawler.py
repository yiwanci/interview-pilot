"""
LeetCode 爬虫
通过 GraphQL API 获取题目信息
"""
import json
from typing import Optional
import httpx

from storage import RawDocument
from .base_crawler import BaseCrawler


class LeetCodeCrawler(BaseCrawler):
    """
    LeetCode 爬虫
    
    使用 LeetCode 的 GraphQL API
    
    使用示例:
        crawler = LeetCodeCrawler()
        
        # 搜索题目
        docs = crawler.search("两数之和", limit=10)
        
        # 按公司标签获取
        docs = crawler.get_by_company("bytedance", limit=50)
        
        # 获取单题详情
        doc = crawler.get_problem("two-sum")
    """
    
    SOURCE_NAME = "leetcode"
    
    # LeetCode CN
    BASE_URL = "https://leetcode.cn"
    GRAPHQL_URL = "https://leetcode.cn/graphql"
    
    def __init__(self):
        super().__init__()
        self.client = httpx.Client(
            headers={
                **self.headers,
                "Content-Type": "application/json",
                "Referer": self.BASE_URL,
            },
            timeout=30,
        )
    
    def search(self, keyword: str, limit: int = 20) -> list[RawDocument]:
        """搜索题目"""
        query = """
        query problemsetQuestionList($categorySlug: String, $limit: Int, $skip: Int, $filters: QuestionListFilterInput) {
            problemsetQuestionList(
                categorySlug: $categorySlug
                limit: $limit
                skip: $skip
                filters: $filters
            ) {
                questions {
                    titleSlug
                    title
                    titleCn
                    difficulty
                    acRate
                    topicTags {
                        name
                        nameTranslated
                    }
                }
            }
        }
        """
        
        variables = {
            "categorySlug": "",
            "skip": 0,
            "limit": limit,
            "filters": {
                "searchKeywords": keyword
            }
        }
        
        try:
            response = self.client.post(
                self.GRAPHQL_URL,
                json={"query": query, "variables": variables}
            )
            data = response.json()
            questions = data.get("data", {}).get("problemsetQuestionList", {}).get("questions", [])
            
            docs = []
            for q in questions:
                # 获取详情
                detail = self.get_problem(q["titleSlug"])
                if detail:
                    docs.append(detail)
            
            return docs
        
        except Exception as e:
            print(f"搜索失败: {e}")
            return []
    
    def crawl_detail(self, url: str) -> Optional[RawDocument]:
        """从 URL 爬取题目详情"""
        # 从 URL 提取 titleSlug
        # https://leetcode.cn/problems/two-sum/
        parts = url.rstrip('/').split('/')
        if 'problems' in parts:
            idx = parts.index('problems')
            if idx + 1 < len(parts):
                title_slug = parts[idx + 1]
                return self.get_problem(title_slug)
        return None
    
    def get_problem(self, title_slug: str) -> Optional[RawDocument]:
        """
        获取单题详情
        
        Args:
            title_slug: 题目标识，如 "two-sum"
        """
        query = """
        query questionData($titleSlug: String!) {
            question(titleSlug: $titleSlug) {
                questionId
                title
                titleSlug
                titleCn
                content
                translatedContent
                difficulty
                topicTags {
                    name
                    nameTranslated
                }
                companyTags {
                    name
                    nameTranslated
                }
                stats
                hints
                solution {
                    content
                }
            }
        }
        """
        
        try:
            response = self.client.post(
                self.GRAPHQL_URL,
                json={"query": query, "variables": {"titleSlug": title_slug}}
            )
            data = response.json()
            q = data.get("data", {}).get("question")
            
            if not q:
                return None
            
            # 构建内容
            content_parts = []
            
            # 题目描述
            desc = q.get("translatedContent") or q.get("content") or ""
            # 简单清理 HTML
            import re
            desc = re.sub(r'<[^>]+>', '', desc)
            content_parts.append(f"【题目描述】\n{desc}")
            
            # 难度
            content_parts.append(f"\n【难度】{q.get('difficulty', '未知')}")
            
            # 标签
            tags = [t.get("nameTranslated") or t.get("name") for t in q.get("topicTags", [])]
            if tags:
                content_parts.append(f"【标签】{', '.join(tags)}")
            
            # 公司标签
            companies = [c.get("nameTranslated") or c.get("name") for c in q.get("companyTags", [])]
            if companies:
                content_parts.append(f"【公司】{', '.join(companies[:10])}")
            
            # 提示
            hints = q.get("hints", [])
            if hints:
                content_parts.append(f"\n【提示】")
                for i, hint in enumerate(hints, 1):
                    content_parts.append(f"{i}. {hint}")
            
            # 官方题解
            solution = q.get("solution", {})
            if solution and solution.get("content"):
                sol_content = re.sub(r'<[^>]+>', '', solution["content"])
                content_parts.append(f"\n【官方题解】\n{sol_content[:2000]}")  # 截断
            
            return self._create_document(
                url=f"{self.BASE_URL}/problems/{title_slug}/",
                title=q.get("titleCn") or q.get("title") or title_slug,
                content="\n".join(content_parts),
                metadata={
                    "question_id": q.get("questionId"),
                    "title_slug": title_slug,
                    "difficulty": q.get("difficulty"),
                    "tags": tags,
                    "companies": companies,
                }
            )
        
        except Exception as e:
            print(f"获取题目失败: {e}")
            return None
    
    def get_by_company(self, company: str, limit: int = 50) -> list[RawDocument]:
        """
        按公司标签获取题目
        
        Args:
            company: 公司名，如 "bytedance", "alibaba", "tencent"
            limit: 数量限制
        """
        query = """
        query companyTag($slug: String!) {
            companyTag(slug: $slug) {
                name
                questions {
                    titleSlug
                    title
                    titleCn
                    difficulty
                }
            }
        }
        """
        
        try:
            response = self.client.post(
                self.GRAPHQL_URL,
                json={"query": query, "variables": {"slug": company}}
            )
            data = response.json()
            questions = data.get("data", {}).get("companyTag", {}).get("questions", [])
            
            docs = []
            for q in questions[:limit]:
                detail = self.get_problem(q["titleSlug"])
                if detail:
                    docs.append(detail)
            
            return docs
        
        except Exception as e:
            print(f"获取公司题目失败: {e}")
            return []
    
    def get_hot_problems(self, limit: int = 100) -> list[RawDocument]:
        """获取热门题目"""
        return self.search("", limit=limit)
