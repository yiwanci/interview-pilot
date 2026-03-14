"""
记忆管理器
整合 Mem0 + SQLite + SM-2，对外提供统一接口
"""
import uuid
from datetime import datetime, date, timedelta
from typing import Optional

from storage import SQLiteStore, KnowledgePoint, StudyLog, ActivityType
from .mem0_client import Mem0Client
from .sm2_engine import SM2Engine, SM2Result


class MemoryManager:
    """
    记忆管理器 - 核心类
    
    职责：
    1. 知识点的增删改查 + 遗忘曲线管理
    2. 学习日志记录
    3. 语义记忆管理（通过 Mem0）
    4. 为 Agent 提供记忆上下文
    
    使用示例:
        mm = MemoryManager()
        
        # 学习新知识点
        mm.learn_new_topic("Redis RDB持久化", "database", "java_backend", ["Redis", "持久化"])
        
        # 复习并更新遗忘曲线
        mm.review_topic(knowledge_id, score=4)
        
        # 获取今日学习计划
        plan = mm.get_today_plan()
        
        # 获取 Agent 上下文
        context = mm.get_context_for_agent("Redis持久化怎么实现")
    """
    
    def __init__(self):
        self.db = SQLiteStore()
        self.mem0 = Mem0Client()
        self.sm2 = SM2Engine()
    
    # ============ 知识点管理 ============
    
    def learn_new_topic(
        self,
        name: str,
        category: str,
        domain: str,
        tags: list[str] = None,
        difficulty: int = 3,
        initial_feedback: str = None,
    ) -> str:
        """
        学习新知识点
        
        Args:
            name: 知识点名称
            category: 分类
            domain: 领域
            tags: 标签列表
            difficulty: 难度 1-5
            initial_feedback: 初次学习反馈
        
        Returns:
            知识点 ID
        """
        # 1. 创建知识点记录
        kp = KnowledgePoint(
            id=str(uuid.uuid4()),
            name=name,
            category=category,
            domain=domain,
            tags=tags or [],
            difficulty=difficulty,
            next_review_at=datetime.now() + timedelta(days=1),  # 明天复习
        )
        kp_id = self.db.create_knowledge_point(kp)
        
        # 2. 记录学习日志
        log = StudyLog(
            id=str(uuid.uuid4()),
            date=date.today(),
            knowledge_id=kp_id,
            activity_type=ActivityType.LEARN_NEW.value,
            summary=f"首次学习：{name}",
        )
        self.db.add_study_log(log)
        
        # 3. 添加语义记忆
        if initial_feedback:
            self.mem0.add_knowledge_feedback(name, initial_feedback)
        else:
            self.mem0.add_knowledge_feedback(name, "刚开始学习，尚未深入理解")
        
        return kp_id
    
    def review_topic(
        self,
        knowledge_id: str,
        score: int,
        llm_score: int = None,
        feedback: str = None,
        duration_min: int = 0,
    ) -> SM2Result:
        """
        复习知识点，更新遗忘曲线
        
        Args:
            knowledge_id: 知识点 ID
            score: 最终评分 0-5（用户确认后的）
            llm_score: LLM 评分（可选）
            feedback: 复习反馈
            duration_min: 复习时长
        
        Returns:
            SM2Result: 遗忘曲线计算结果
        """
        # 1. 获取知识点
        kp = self.db.get_knowledge_point(knowledge_id)
        if not kp:
            raise ValueError(f"知识点不存在: {knowledge_id}")
        
        # 2. SM-2 计算
        result = self.sm2.calculate(
            score=score,
            current_ease=kp.ease_factor,
            current_interval=kp.interval_days,
            current_reps=kp.repetitions,
        )
        
        # 3. 更新知识点
        kp.ease_factor = result.ease_factor
        kp.interval_days = result.interval_days
        kp.repetitions = result.repetitions
        kp.mastery_level = result.mastery_level
        kp.last_review_at = datetime.now()
        kp.next_review_at = result.next_review_at
        self.db.update_knowledge_point(kp)
        
        # 4. 记录学习日志
        log = StudyLog(
            id=str(uuid.uuid4()),
            date=date.today(),
            knowledge_id=knowledge_id,
            activity_type=ActivityType.REVIEW.value,
            duration_min=duration_min,
            score=score,
            llm_score=llm_score,
            summary=f"复习「{kp.name}」，评分{score}，掌握度{result.mastery_level:.0%}",
        )
        self.db.add_study_log(log)
        
        # 5. 更新语义记忆
        if feedback:
            self.mem0.add_knowledge_feedback(kp.name, feedback)
        
        mastery_desc = self._get_mastery_description(result.mastery_level)
        self.mem0.add_knowledge_feedback(
            kp.name,
            f"复习评分{score}分，当前{mastery_desc}，下次复习：{result.interval_days}天后"
        )
        
        return result
    
    def get_knowledge_point(self, knowledge_id: str) -> Optional[KnowledgePoint]:
        """获取知识点详情"""
        return self.db.get_knowledge_point(knowledge_id)
    
    def search_knowledge(self, keyword: str, domain: str = None) -> list[KnowledgePoint]:
        """搜索知识点"""
        return self.db.search_knowledge_points(keyword, domain)
    
    # ============ 学习计划 ============
    
    def get_today_plan(self) -> dict:
        """
        获取今日学习计划
        
        Returns:
            {
                "due_reviews": [...],      # 到期需要复习的
                "weak_points": [...],      # 薄弱知识点
                "suggested_new": [...],    # 建议学习的新内容
                "summary": "..."           # 计划摘要
            }
        """
        due_reviews = self.db.get_due_reviews(limit=10)
        weak_points = self.db.get_weak_points(threshold=0.5, limit=5)
        
        # 去重（weak_points 可能和 due_reviews 重叠）
        due_ids = {kp.id for kp in due_reviews}
        weak_points = [kp for kp in weak_points if kp.id not in due_ids]
        
        # 生成摘要
        summary_parts = []
        if due_reviews:
            summary_parts.append(f"今日有 {len(due_reviews)} 个知识点需要复习")
        if weak_points:
            summary_parts.append(f"有 {len(weak_points)} 个薄弱知识点建议加强")
        if not summary_parts:
            summary_parts.append("暂无待复习内容，可以学习新知识点")
        
        return {
            "due_reviews": due_reviews,
            "weak_points": weak_points,
            "summary": "；".join(summary_parts),
        }
    
    def get_weekly_report(self) -> dict:
        """
        获取本周学习报告
        """
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        
        logs = self.db.get_study_logs(start_date=week_start, end_date=today)
        stats = self.db.get_stats()
        
        # 统计
        total_reviews = len([l for l in logs if l.activity_type == ActivityType.REVIEW.value])
        total_new = len([l for l in logs if l.activity_type == ActivityType.LEARN_NEW.value])
        total_duration = sum(l.duration_min or 0 for l in logs)
        
        # 按天统计
        daily_stats = {}
        for log in logs:
            day = str(log.date)
            if day not in daily_stats:
                daily_stats[day] = {"reviews": 0, "new": 0}
            if log.activity_type == ActivityType.REVIEW.value:
                daily_stats[day]["reviews"] += 1
            else:
                daily_stats[day]["new"] += 1
        
        return {
            "period": f"{week_start} ~ {today}",
            "total_reviews": total_reviews,
            "total_new_learned": total_new,
            "total_duration_min": total_duration,
            "daily_stats": daily_stats,
            "overall_stats": stats,
        }
    
    # ============ Agent 上下文 ============
    
    def get_context_for_agent(self, query: str) -> dict:
        """
        为 Agent 提供记忆上下文
        
        Args:
            query: 用户问题
        
        Returns:
            {
                "user_profile": {...},
                "related_knowledge": [...],
                "memory_context": "...",
                "review_status": "...",
            }
        """
        # 1. 用户画像
        profile = self.db.get_full_profile()
        
        # 2. 搜索相关知识点
        related_kps = self.db.search_knowledge_points(query)[:5]
        
        # 3. 搜索语义记忆
        memory_context = self.mem0.get_knowledge_context(query)
        
        # 4. 复习状态
        due_count = len(self.db.get_due_reviews(limit=100))
        
        # 5. 组装知识点信息
        knowledge_info = []
        for kp in related_kps:
            knowledge_info.append({
                "name": kp.name,
                "mastery": kp.mastery_level,
                "mastery_desc": self._get_mastery_description(kp.mastery_level),
                "last_review": str(kp.last_review_at) if kp.last_review_at else "从未复习",
                "next_review": str(kp.next_review_at) if kp.next_review_at else "待安排",
            })
        
        return {
            "user_profile": {
                "target_positions": profile.target_positions,
                "target_companies": profile.target_companies,
                "tech_stack": profile.tech_stack,
            },
            "related_knowledge": knowledge_info,
            "memory_context": memory_context,
            "review_status": f"当前有 {due_count} 个知识点待复习",
        }
    
    def format_context_for_prompt(self, query: str) -> str:
        """
        格式化上下文，直接用于 Prompt
        """
        ctx = self.get_context_for_agent(query)
        
        parts = []
        
        # 用户背景
        profile = ctx["user_profile"]
        if profile["target_positions"]:
            parts.append(f"用户目标岗位：{', '.join(profile['target_positions'])}")
        if profile["target_companies"]:
            parts.append(f"目标公司：{', '.join(profile['target_companies'])}")
        
        # 相关知识掌握情况
        if ctx["related_knowledge"]:
            parts.append("\n相关知识点掌握情况：")
            for k in ctx["related_knowledge"]:
                parts.append(f"- {k['name']}：{k['mastery_desc']}（上次复习：{k['last_review']}）")
        
        # 语义记忆
        if ctx["memory_context"]:
            parts.append(f"\n历史学习记录：\n{ctx['memory_context']}")
        
        # 复习状态
        parts.append(f"\n{ctx['review_status']}")
        
        return "\n".join(parts)
    
    # ============ 用户画像 ============
    
    def set_user_profile(
        self,
        target_positions: list[str] = None,
        target_companies: list[str] = None,
        tech_stack: list[str] = None,
    ):
        """设置用户画像"""
        if target_positions:
            self.db.set_profile("target_positions", target_positions)
            self.mem0.add_preference(f"目标岗位：{', '.join(target_positions)}")
        if target_companies:
            self.db.set_profile("target_companies", target_companies)
            self.mem0.add_preference(f"目标公司：{', '.join(target_companies)}")
        if tech_stack:
            self.db.set_profile("tech_stack", tech_stack)
            self.mem0.add_preference(f"技术栈：{', '.join(tech_stack)}")
    
    # ============ 辅助方法 ============
    
    @staticmethod
    def _get_mastery_description(mastery: float) -> str:
        """掌握程度描述"""
        if mastery >= 0.9:
            return "完全掌握"
        elif mastery >= 0.7:
            return "基本掌握"
        elif mastery >= 0.5:
            return "部分掌握"
        elif mastery >= 0.3:
            return "初步了解"
        else:
            return "刚开始学"
