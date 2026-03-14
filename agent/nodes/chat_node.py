"""
闲聊节点
处理通用对话
"""
from openai import OpenAI

from config import get_llm_config
from memory import MemoryManager
from agent.state import AgentState


CHAT_SYSTEM_PROMPT = """你是一个友好的面试准备助手 InterviewPilot。

你可以帮助用户：
1. 学习技术知识（输入「讲讲 xxx」）
2. 模拟面试练习（输入「考考我」）
3. 制定学习计划（输入「今天学什么」）
4. 搜集面经资料（输入「搜集 xxx 面经」）

用户背景：
{memory_context}

请友好地回复用户，如果用户意图不明确，可以引导他使用上述功能。"""


class ChatNode:
    """
    闲聊节点
    处理不属于其他意图的通用对话
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
        """闲聊节点处理"""
        user_input = state.get("user_input", "")
        
        try:
            # 获取记忆上下文
            memory_context = ""
            try:
                memory_context = self.memory_manager.format_context_for_prompt(user_input)
            except Exception:
                memory_context = "暂无用户背景信息"
            
            system_prompt = CHAT_SYSTEM_PROMPT.format(
                memory_context=memory_context or "暂无用户背景信息"
            )
            
            response = self.llm_client.chat.completions.create(
                model=self.llm_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_input},
                ],
                temperature=0.8,
            )
            
            state["response"] = response.choices[0].message.content.strip()
        
        except Exception as e:
            state["error"] = str(e)
            state["response"] = self._fallback_response()
        
        return state
    
    def _fallback_response(self) -> str:
        """兜底回复"""
        return """你好！我是 InterviewPilot，你的面试准备助手。

我可以帮你：
📚 学习知识 - 输入「讲讲 Redis」
📝 模拟面试 - 输入「考考我」
📅 学习计划 - 输入「今天学什么」
🔍 搜集面经 - 输入「搜集字节面经」

请问有什么可以帮你的？"""


def chat_node(state: AgentState) -> AgentState:
    """函数式调用"""
    node = ChatNode()
    return node(state)
