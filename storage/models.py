"""
数据模型定义
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from enum import Enum


class Domain(str, Enum):
    """知识领域"""
    JAVA_BACKEND = "java_backend"
    AI_AGENT = "ai_agent"
    LLM_ALGORITHM = "llm_algorithm"
    CS_BASIC = "cs_basic"


class ActivityType(str, Enum):
    """学习活动类型"""
    LEARN_NEW = "learn_new"        # 学新知识
    REVIEW = "review"              # 复习
    MOCK_INTERVIEW = "mock_interview"  # 模拟面试


@dataclass
class KnowledgePoint:
    """知识点"""
    id: str
    name: str                          # "Redis RDB持久化"
    category: str                      # "database"
    domain: str                        # "java_backend"
    tags: list[str] = field(default_factory=list)
    difficulty: int = 3                # 难度 1-5
    
    # SM-2 遗忘曲线字段
    ease_factor: float = 2.5
    interval_days: int = 0
    repetitions: int = 0
    mastery_level: float = 0.0         # 掌握程度 0~1
    
    # 时间
    last_review_at: Optional[datetime] = None
    next_review_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)
    
    # 关联
    mem0_memory_ids: list[str] = field(default_factory=list)
    related_qa_ids: list[str] = field(default_factory=list)


@dataclass
class StudyLog:
    """学习日志"""
    id: str
    date: datetime
    knowledge_id: Optional[str] = None  # 关联知识点，可空
    activity_type: str = ActivityType.LEARN_NEW.value
    duration_min: int = 0               # 学习时长（分钟）
    score: Optional[int] = None         # 最终评分 0-5
    llm_score: Optional[int] = None     # LLM评分
    user_score: Optional[int] = None    # 用户自评
    summary: str = ""                   # 学习摘要
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class UserProfile:
    """用户画像"""
    user_name: str = ""
    target_positions: list[str] = field(default_factory=list)   # 目标岗位
    target_companies: list[str] = field(default_factory=list)   # 目标公司
    tech_stack: list[str] = field(default_factory=list)         # 技术栈
    weak_areas: list[str] = field(default_factory=list)         # 薄弱领域
    study_preference: dict = field(default_factory=dict)        # 学习偏好


@dataclass
class RawDocument:
    """爬取的原始文档"""
    id: str
    source: str                        # "xiaohongshu" / "douyin" / "leetcode"
    url: str
    title: str
    content: str
    author: str = ""
    likes: int = 0
    crawled_at: datetime = field(default_factory=datetime.now)
    metadata: dict = field(default_factory=dict)


@dataclass
class DocumentChunk:
    """分块后的文档"""
    id: str
    doc_id: str                        # 原始文档ID
    content: str                       # 分块内容
    chunk_type: str = "text"           # "qa" / "text" / "code"
    
    # 元数据
    source: str = ""
    domain: str = ""
    category: str = ""
    tags: list[str] = field(default_factory=list)
    
    # 向量
    embedding: Optional[list[float]] = None
    
    # 额外信息（面经Q&A用）
    question: str = ""                 # 如果是Q&A类型
    answer: str = ""
    company: str = ""
    position: str = ""


@dataclass
class Conversation:
    """对话会话"""
    id: str
    title: str = "新对话"                    # 会话标题
    user_name: str = ""                      # 关联用户名
    session_id: str = ""                     # 会话标识（UI生成）
    metadata: dict = field(default_factory=dict)  # 额外元数据

    # 时间
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    # 统计
    message_count: int = 0                   # 消息总数
    last_message: Optional[str] = None       # 最后一条消息摘要


@dataclass
class Message:
    """对话消息"""
    id: str
    conversation_id: str                     # 关联会话ID
    role: str                                # "user" 或 "assistant"
    content: str                             # 消息内容
    timestamp: datetime = field(default_factory=datetime.now)

    # 元数据
    session_id: str = ""                     # 会话标识
    intent: str = ""                         # 意图类型（study/interview等）
    response_time_ms: Optional[int] = None   # 响应时间（毫秒）
    tokens_used: Optional[int] = None        # 消耗token数

    # 跟踪信息（可选）
    trace: list = field(default_factory=list)  # 执行跟踪信息
