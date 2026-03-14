"""
学习规划相关 Prompt
"""

DAILY_PLAN_PROMPT = """请根据用户的学习情况，生成今日学习计划。

用户背景：
{user_profile}

待复习知识点（遗忘曲线到期）：
{due_reviews}

薄弱知识点：
{weak_points}

最近学习记录：
{recent_logs}

要求：
1. 优先安排到期的复习内容
2. 合理分配时间，不要太多
3. 给出具体的学习建议
4. 预估总学习时长

请生成今日学习计划："""


WEEKLY_REPORT_PROMPT = """请根据学习数据生成周报总结。

本周数据：
{weekly_stats}

知识点掌握情况：
{mastery_overview}

要求：
1. 总结本周学习成果
2. 指出进步和不足
3. 给出下周建议
4. 语气要鼓励性

请生成周报："""


CHAT_SYSTEM_PROMPT = """你是一个友好的面试准备助手。

你可以：
1. 回答技术问题
2. 提供学习建议
3. 解答面试相关疑问
4. 闲聊鼓励用户

用户背景：
{memory_context}

请友好地回复用户。"""
