"""
学习规划节点
"""
from openai import OpenAI

from config import get_llm_config
from memory import MemoryManager
from agent.state import AgentState
from agent.prompts.plan_prompt import DAILY_PLAN_PROMPT, WEEKLY_REPORT_PROMPT


class PlanNode:
    """
    学习规划节点
    
    功能：
    - 生成今日学习计划
    - 生成周报
    - 查询学习进度
    """
    
    def __init__(self):
        config = get_llm_config()
        self.llm_client = OpenAI(
            api_key=config["api_key"],
            base_url=config["base_url"],
        )
        self.llm_model = config["model"]
        self.memory_manager = MemoryManager()
    
    def __call__(self, state: AgentState) -> AgentState:
        """规划节点处理"""
        user_input = state.get("user_input", "").lower()
        
        try:
            if "周报" in user_input or "本周" in user_input:
                return self._weekly_report(state)
            elif "进度" in user_input or "统计" in user_input:
                return self._show_progress(state)
            else:
                return self._daily_plan(state)
        
        except Exception as e:
            state["error"] = str(e)
            state["response"] = f"抱歉，处理时出错了：{e}"
        
        return state
    
    def _safe_join(self, items, default="未设置"):
        """安全地 join 列表"""
        if not items:
            return default
        if not isinstance(items, (list, tuple)):
            return str(items) if items else default
        return ', '.join(str(item) for item in items) if items else default
    
    def _daily_plan(self, state: AgentState) -> AgentState:
        """生成今日计划"""
        # 获取数据
        plan = self.memory_manager.get_today_plan()
        profile = self.memory_manager.db.get_full_profile()
        
        # 格式化待复习
        due_reviews = plan.get("due_reviews", [])
        if due_reviews:
            due_str = "\n".join([
                f"- {kp.name}（掌握度：{kp.mastery_level:.0%}，距上次复习：{self._days_since(kp.last_review_at)}天）"
                for kp in due_reviews
            ])
        else:
            due_str = "无"
        
        # 格式化薄弱点
        weak_points = plan.get("weak_points", [])
        if weak_points:
            weak_str = "\n".join([
                f"- {kp.name}（掌握度：{kp.mastery_level:.0%}）"
                for kp in weak_points
            ])
        else:
            weak_str = "无"
        
        # 格式化用户画像（使用安全方法）
        profile_str = f"""目标岗位：{self._safe_join(profile.target_positions)}
目标公司：{self._safe_join(profile.target_companies)}
技术栈：{self._safe_join(profile.tech_stack)}"""
        
        # 生成计划
        prompt = DAILY_PLAN_PROMPT.format(
            user_profile=profile_str,
            due_reviews=due_str,
            weak_points=weak_str,
            recent_logs="最近3天学习记录（简化显示）",
        )
        
        response = self.llm_client.chat.completions.create(
            model=self.llm_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )
        
        plan_text = response.choices[0].message.content.strip()
        
        state["response"] = f"📅 今日学习计划\n\n{plan_text}"
        return state
    
    def _weekly_report(self, state: AgentState) -> AgentState:
        """生成周报"""
        report = self.memory_manager.get_weekly_report()
        
        stats_str = f"""学习周期：{report['period']}
复习次数：{report['total_reviews']} 次
新学知识点：{report['total_new_learned']} 个
总学习时长：{report['total_duration_min']} 分钟"""
        
        overall = report.get("overall_stats", {})
        mastery_str = f"""知识点总数：{overall.get('total_knowledge_points', 0)}
已掌握：{overall.get('mastered_count', 0)}
待复习：{overall.get('due_review_count', 0)}"""
        
        prompt = WEEKLY_REPORT_PROMPT.format(
            weekly_stats=stats_str,
            mastery_overview=mastery_str,
        )
        
        response = self.llm_client.chat.completions.create(
            model=self.llm_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )
        
        report_text = response.choices[0].message.content.strip()
        
        state["response"] = f"📊 本周学习报告\n\n{report_text}"
        return state
    
    def _show_progress(self, state: AgentState) -> AgentState:
        """显示学习进度"""
        stats = self.memory_manager.db.get_stats()
        
        total = max(stats['total_knowledge_points'], 1)
        mastery_rate = stats['mastered_count'] / total
        
        progress = f"""📈 学习进度统计

知识点总数：{stats['total_knowledge_points']}
已掌握（≥80%）：{stats['mastered_count']}
待复习：{stats['due_review_count']}
学习记录：{stats['total_study_logs']} 条

掌握率：{mastery_rate:.0%}
"""
        
        state["response"] = progress
        return state
    
    def _days_since(self, dt) -> int:
        """计算距今天数"""
        if not dt:
            return 999
        from datetime import datetime
        if isinstance(dt, str):
            try:
                dt = datetime.fromisoformat(dt)
            except ValueError:
                return 999
        return (datetime.now() - dt).days


def plan_node(state: AgentState) -> AgentState:
    """函数式调用"""
    node = PlanNode()
    return node(state)
