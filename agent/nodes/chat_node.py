"""
闲聊节点
处理通用对话
"""
import re
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
        config = get_llm_config(node_name="chat")
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
            extracted_name = self._extract_user_name(user_input)
            if extracted_name:
                self.memory_manager.set_user_name(extracted_name)
                state["response"] = f"记住啦，你叫{extracted_name}。之后你问我“我叫什么名字”我就能回答。"
                return state

            if self._is_ask_user_name(user_input):
                user_name = self.memory_manager.get_user_name()
                if user_name:
                    state["response"] = f"你叫{user_name}。"
                else:
                    state["response"] = "我还不知道你的名字，你可以直接说“我叫xxx”。"
                return state

            # 获取记忆上下文
            memory_context = ""
            try:
                memory_context = self.memory_manager.format_context_for_prompt(user_input)
            except Exception:
                memory_context = "暂无用户背景信息"
            
            system_prompt = CHAT_SYSTEM_PROMPT.format(
                memory_context=memory_context or "暂无用户背景信息"
            )

            # 获取对话历史
            conversation_history = state.get("conversation_history", [])
            # 限制历史长度（保留最近20轮对话）
            max_history_rounds = 20
            if len(conversation_history) > max_history_rounds * 2:
                conversation_history = conversation_history[-(max_history_rounds * 2):]

            # 构建消息列表：system + 历史对话 + 当前用户输入
            messages = [{"role": "system", "content": system_prompt}]
            messages.extend(conversation_history)  # 历史对话消息
            messages.append({"role": "user", "content": user_input})

            # 流式调用 LLM
            stream = self.llm_client.chat.completions.create(
                model=self.llm_model,
                messages=messages,
                temperature=0.8,
                stream=True,
            )

            # 收集流式响应
            collected_chunks = []
            collected_content = ""
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    collected_chunks.append(chunk)
                    collected_content += content

            state["response"] = collected_content.strip()
        
        except Exception as e:
            state["error"] = str(e)
            state["response"] = self._fallback_response()
        
        return state

    def _extract_user_name(self, text: str) -> str:
        patterns = [
            r"我叫\s*([^\s，。！？,!.?]{1,20})",
            r"我是\s*([^\s，。！？,!.?]{1,20})",
            r"我的名字是\s*([^\s，。！？,!.?]{1,20})",
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                candidate = match.group(1).strip()
                invalid_keywords = ["什么", "几", "谁", "吗", "么", "?", "？"]
                if any(kw in candidate for kw in invalid_keywords):
                    return ""
                return candidate
        return ""

    @staticmethod
    def _is_ask_user_name(text: str) -> bool:
        text_lower = text.lower()
        return "我叫什么" in text or "我的名字" in text or "who am i" in text_lower
    
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
