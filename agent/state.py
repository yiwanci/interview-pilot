"""
LangGraph 状态定义
"""
from typing import TypedDict, Optional, Literal


class AgentState(TypedDict, total=False):
    """
    Agent 状态
    在 LangGraph 节点之间传递
    """
    # 用户输入
    user_input: str
    
    # 意图识别结果
    intent: Literal["study", "interview", "crawl", "plan", "chat"]
    
    # 记忆上下文
    memory_context: dict
    
    # RAG 检索结果
    rag_results: list
    
    # 中间处理结果
    extracted_topic: str          # 提取的主题/知识点
    selected_questions: list      # 选中的面试题
    crawl_keyword: str            # 爬取关键词
    crawl_source: str             # 爬取来源
    
    # 评分相关
    user_answer: str              # 用户回答
    llm_score: int                # LLM 评分
    score_feedback: str           # 评分反馈
    
    # 最终输出
    response: str
    
    # 控制标志
    should_update_memory: bool
    error: Optional[str]
