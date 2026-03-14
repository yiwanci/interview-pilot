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
    3. RAG 检索相关资料
    4. 生成讲解
    5. 更新记忆
    """
    
    def __init__(self):
        config = get_llm_config()
        self.llm_client = OpenAI(
            api_key=config["api_key"],
            base_url=config["base_url"],
        )
        self.llm_model = config["model"]
        self.memory_manager = MemoryManager()
        self.rag = RAGPipeline()
    
    def __call__(self, state: AgentState) -> AgentState:
        """学习节点处理"""
        user_input = state.get("user_input", "")
        
        try:
            # 1. 提取主题
            topic = self._extract_topic(user_input)
            state["extracted_topic"] = topic
            
            # 2. 获取记忆上下文
            memory_context = self.memory_manager.format_context_for_prompt(topic)
            state["memory_context"] = {"raw": memory_context}
            
            # 3. RAG 检索
            rag_result = self.rag.query(
                question=user_input,
                memory_context=memory_context,
                top_k=5,
            )
            state["rag_results"] = rag_result.get("sources", [])
            
            # 4. 生成回答
            response = self._generate_response(
                question=user_input,
                memory_context=memory_context,
                rag_context=self._format_rag_context(rag_result.get("sources", [])),
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
    ) -> str:
        """生成讲解"""
        system_prompt = STUDY_SYSTEM_PROMPT.format(
            memory_context=memory_context or "暂无背景信息",
            rag_context=rag_context or "暂无相关资料",
        )
        
        user_prompt = STUDY_USER_PROMPT.format(question=question)
        
        response = self.llm_client.chat.completions.create(
            model=self.llm_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7,
        )
        
        return response.choices[0].message.content.strip()
    
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
