"""
模拟面试节点
"""
import re
from openai import OpenAI

from config import get_llm_config
from memory import MemoryManager
from rag import RAGPipeline
from agent.state import AgentState
from agent.prompts.interview_prompt import (
    INTERVIEW_SYSTEM_PROMPT,
    ASK_QUESTION_PROMPT,
    EVALUATE_ANSWER_PROMPT,
)


class InterviewNode:
    """
    模拟面试节点

    两种模式：
    1. 出题模式：根据薄弱点选题提问
    2. 评分模式：评估用户回答
    """

    def __init__(self):
        config = get_llm_config(node_name="interview")
        self.llm_client = OpenAI(
            api_key=config["api_key"],
            base_url=config["base_url"],
        )
        self.llm_model = config["model"]
        self.memory_manager = MemoryManager()
        try:
            self.rag = RAGPipeline()
            self.rag_available = self.rag.available
        except Exception as e:
            print(f"[WARNING] RAG not available: {e}")
            self.rag = None
            self.rag_available = False
    
    def __call__(self, state: AgentState) -> AgentState:
        """面试节点处理"""
        user_input = state.get("user_input", "")
        
        try:
            # 判断是出题还是回答
            if self._is_asking_for_question(user_input):
                return self._ask_question(state)
            else:
                return self._evaluate_answer(state)
        
        except Exception as e:
            state["error"] = str(e)
            state["response"] = f"抱歉，处理时出错了：{e}"
        
        return state
    
    def _is_asking_for_question(self, text: str) -> bool:
        """判断是否在请求出题"""
        keywords = ["考考我", "出题", "来道题", "下一题", "开始", "模拟面试"]
        return any(kw in text for kw in keywords)
    
    def _ask_question(self, state: AgentState) -> AgentState:
        """出题"""
        # 1. 获取待复习知识点
        plan = self.memory_manager.get_today_plan()
        due_reviews = plan.get("due_reviews", [])
        weak_points = plan.get("weak_points", [])

        # 合并并格式化
        all_points = due_reviews + weak_points
        if not all_points:
            state["response"] = "你目前没有待复习的知识点，要不先学点新内容？"
            return state

        knowledge_str = "\n".join([
            f"- {kp.name}（掌握度：{kp.mastery_level:.0%}）"
            for kp in all_points[:10]
        ])

        # 2. 检索相关面试题（如果RAG可用）
        reference_questions = []
        if self.rag_available and self.rag:
            try:
                topics = [kp.name for kp in all_points[:3]]
                for topic in topics:
                    results = self.rag.retrieve(topic, top_k=2)
                    for r in results:
                        if hasattr(r, 'question') and r.question:
                            reference_questions.append(r.question)
            except Exception as e:
                print(f"[WARNING] RAG retrieve failed: {e}")

        ref_str = "\n".join([f"- {q}" for q in reference_questions[:5]]) or "无"
        
        # 3. 生成问题
        prompt = ASK_QUESTION_PROMPT.format(
            knowledge_points=knowledge_str,
            reference_questions=ref_str,
        )

        # 获取对话历史
        conversation_history = state.get("conversation_history", [])

        # 限制历史长度（保留最近20轮对话）
        max_history_rounds = 20
        if len(conversation_history) > max_history_rounds * 2:
            conversation_history = conversation_history[-(max_history_rounds * 2):]

        # 构建消息：历史对话 + 当前提示
        messages = conversation_history.copy()  # 历史对话消息
        messages.append({"role": "user", "content": prompt})

        # 流式调用 LLM
        stream = self.llm_client.chat.completions.create(
            model=self.llm_model,
            messages=messages,
            temperature=0.7,
            stream=True,
        )

        # 收集流式响应
        collected_content = ""
        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                collected_content += content

        question = collected_content.strip()
        
        state["selected_questions"] = [question]
        state["response"] = f"📝 面试问题：\n\n{question}\n\n请回答（回答后我会给你评分）："
        
        return state
    
    def _evaluate_answer(self, state: AgentState) -> AgentState:
        """评估回答"""
        user_answer = state.get("user_input", "")

        # 获取上一个问题（简化处理，实际应该从会话历史获取）
        selected = state.get("selected_questions", [])
        if not selected:
            state["response"] = "请先让我出一道题，输入「考考我」开始。"
            return state

        question = selected[0]

        # 检索参考答案（如果RAG可用）
        reference_points = "无参考资料"
        if self.rag_available and self.rag:
            try:
                rag_results = self.rag.retrieve(question, top_k=3)
                if rag_results:
                    reference_points = "\n".join([
                        f"- {r.content[:200]}" for r in rag_results
                    ])
            except Exception as e:
                print(f"[WARNING] RAG retrieve failed: {e}")
        
        # 评估
        prompt = EVALUATE_ANSWER_PROMPT.format(
            question=question,
            answer=user_answer,
            reference_points=reference_points,
        )

        # 获取对话历史
        conversation_history = state.get("conversation_history", [])

        # 限制历史长度（保留最近20轮对话）
        max_history_rounds = 20
        if len(conversation_history) > max_history_rounds * 2:
            conversation_history = conversation_history[-(max_history_rounds * 2):]

        # 构建消息：历史对话 + 当前提示
        messages = conversation_history.copy()  # 历史对话消息
        messages.append({"role": "user", "content": prompt})

        # 流式调用 LLM
        stream = self.llm_client.chat.completions.create(
            model=self.llm_model,
            messages=messages,
            temperature=0.3,
            stream=True,
        )

        # 收集流式响应
        collected_content = ""
        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                collected_content += content

        evaluation = collected_content.strip()
        
        # 提取分数
        score = self._extract_score(evaluation)
        state["llm_score"] = score
        state["score_feedback"] = evaluation
        state["should_update_memory"] = True
        
        state["response"] = f"📊 评估结果：\n\n{evaluation}\n\n---\n输入「下一题」继续，或问我其他问题。"
        
        return state
    
    def _extract_score(self, evaluation: str) -> int:
        """从评估结果提取分数"""
        # 尝试匹配 "评分：X" 或 "X分"
        patterns = [
            r'评分[：:]\s*(\d)',
            r'(\d)\s*分',
            r'得分[：:]\s*(\d)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, evaluation)
            if match:
                return int(match.group(1))
        
        return 3  # 默认中等分数


def interview_node(state: AgentState) -> AgentState:
    """函数式调用"""
    node = InterviewNode()
    return node(state)
