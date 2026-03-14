"""
意图路由节点
识别用户意图，分发到对应处理节点
"""
from openai import OpenAI

from config import get_llm_config
from agent.state import AgentState


class RouterNode:
    """
    意图路由器
    
    识别用户意图：
    - study: 学习/讲解某个知识点
    - interview: 模拟面试/做题
    - crawl: 爬取/搜集面经
    - plan: 学习计划/进度查询
    - chat: 闲聊/其他
    """
    
    INTENT_PROMPT = """请判断用户的意图类型。

意图类型：
- study: 想学习或了解某个技术知识点（如"讲讲Redis"、"什么是JVM"）
- interview: 想做模拟面试或练习题目（如"考考我"、"来道题"、"模拟面试"）
- crawl: 想搜集或导入面经资料（如"搜集字节面经"、"导入数据"）
- plan: 想查看学习计划或进度（如"今天学什么"、"我的进度"、"周报"）
- chat: 闲聊或其他（如"你好"、"谢谢"）

用户输入：{user_input}

只返回意图类型（study/interview/crawl/plan/chat）："""

    def __init__(self):
        config = get_llm_config()
        self.llm_client = OpenAI(
            api_key=config["api_key"],
            base_url=config["base_url"],
        )
        self.llm_model = config["model"]
    
    def __call__(self, state: AgentState) -> AgentState:
        """路由节点"""
        user_input = state.get("user_input", "")
        
        # 快速规则匹配
        intent = self._quick_match(user_input)
        
        # 规则匹配失败，用 LLM
        if not intent:
            intent = self._llm_classify(user_input)
        
        state["intent"] = intent
        return state
    
    def _quick_match(self, text: str) -> str:
        """快速规则匹配"""
        text_lower = text.lower()
        
        # 面试相关
        interview_keywords = ["考考我", "模拟面试", "来道题", "出题", "面试题", "测试一下"]
        if any(kw in text_lower for kw in interview_keywords):
            return "interview"
        
        # 爬取相关
        crawl_keywords = ["搜集", "爬取", "导入", "抓取", "面经"]
        if any(kw in text_lower for kw in crawl_keywords):
            return "crawl"
        
        # 计划相关
        plan_keywords = ["计划", "进度", "今天学", "周报", "复习什么", "安排"]
        if any(kw in text_lower for kw in plan_keywords):
            return "plan"
        
        # 学习相关
        study_keywords = ["讲讲", "什么是", "介绍", "解释", "怎么", "如何", "原理"]
        if any(kw in text_lower for kw in study_keywords):
            return "study"
        
        return ""
    
    def _llm_classify(self, user_input: str) -> str:
        """LLM 意图分类"""
        try:
            response = self.llm_client.chat.completions.create(
                model=self.llm_model,
                messages=[{
                    "role": "user",
                    "content": self.INTENT_PROMPT.format(user_input=user_input)
                }],
                temperature=0.1,
                max_tokens=20,
            )
            
            intent = response.choices[0].message.content.strip().lower()
            
            # 验证
            valid_intents = ["study", "interview", "crawl", "plan", "chat"]
            if intent in valid_intents:
                return intent
            
            return "chat"
        
        except Exception:
            return "chat"


def router_node(state: AgentState) -> AgentState:
    """函数式调用"""
    router = RouterNode()
    return router(state)
