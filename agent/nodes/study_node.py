"""
学习辅导节点
"""
from openai import OpenAI

from config import get_llm_config
from memory import MemoryManager
from rag import RAGPipeline
from agent.state import AgentState
from agent.prompts.study_prompt import (
    STUDY_SYSTEM_PROMPT,
    STUDY_USER_PROMPT,
    TOPIC_EXTRACT_PROMPT,
)


class StudyNode:
    """
    学习辅导节点

    流程：
    1. 提取学习主题
    2. 获取记忆上下文
    3. RAG 检索相关资料（如果可用）
    4. 生成讲解
    5. 更新记忆
    """

    def __init__(self):
        config = get_llm_config(node_name="study")
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
        """学习节点处理"""
        user_input = state.get("user_input", "")
        conversation_history = state.get("conversation_history", [])

        try:
            # 1. 提取主题
            topic = self._extract_topic(user_input)
            state["extracted_topic"] = topic

            # 2. 获取记忆上下文
            memory_context = self.memory_manager.format_context_for_prompt(topic)
            state["memory_context"] = {"raw": memory_context}

            # 3. RAG 检索（如果可用）
            rag_sources = []
            if self.rag_available and self.rag:
                try:
                    rag_result = self.rag.query(
                        question=user_input,
                        memory_context=memory_context,
                        top_k=5,
                    )
                    rag_sources = rag_result.get("sources", [])
                except Exception as e:
                    print(f"[WARNING] RAG query failed: {e}")
                    rag_sources = []

            state["rag_results"] = rag_sources

            # 4. 生成回答
            response = self._generate_response(
                question=user_input,
                memory_context=memory_context,
                rag_context=self._format_rag_context(rag_sources),
                conversation_history=conversation_history,
            )
            state["response"] = response

            # 5. 标记需要更新记忆
            state["should_update_memory"] = True

        except Exception as e:
            state["error"] = str(e)
            state["response"] = f"抱歉，处理时出错了：{e}"

        return state
    
    def _extract_topic(self, user_input: str) -> str:
        """提取学习主题"""
        response = self.llm_client.chat.completions.create(
            model=self.llm_model,
            messages=[{
                "role": "user",
                "content": TOPIC_EXTRACT_PROMPT.format(user_input=user_input)
            }],
            temperature=0.1,
            max_tokens=50,
        )
        return response.choices[0].message.content.strip()
    
    def _generate_response(
        self,
        question: str,
        memory_context: str,
        rag_context: str,
        conversation_history: list = None,
    ) -> str:
        """生成讲解"""
        system_prompt = STUDY_SYSTEM_PROMPT.format(
            memory_context=memory_context or "暂无背景信息",
            rag_context=rag_context or "暂无相关资料",
        )
        
        user_prompt = STUDY_USER_PROMPT.format(question=question)
        
        # 处理对话历史
        if conversation_history is None:
            conversation_history = []

        # 限制历史长度（保留最近20轮对话）
        max_history_rounds = 20
        if len(conversation_history) > max_history_rounds * 2:
            conversation_history = conversation_history[-(max_history_rounds * 2):]

        # 构建消息列表：system + 历史对话 + 当前用户输入
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(conversation_history)  # 历史对话消息
        messages.append({"role": "user", "content": user_prompt})

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

        return collected_content.strip()
    
    def _format_rag_context(self, sources: list) -> str:
        """格式化 RAG 结果"""
        if not sources:
            return ""
        
        parts = []
        for i, chunk in enumerate(sources, 1):
            source_tag = f"[{chunk.source}]" if hasattr(chunk, 'source') and chunk.source else ""
            content = chunk.content if hasattr(chunk, 'content') else str(chunk)
            parts.append(f"{i}. {content[:500]} {source_tag}")
        
        return "\n".join(parts)


def study_node(state: AgentState) -> AgentState:
    """函数式调用"""
    node = StudyNode()
    return node(state)
