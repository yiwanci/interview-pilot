"""
LangGraph 主流程图
"""
import time
from datetime import datetime
from langgraph.graph import StateGraph, END

from .state import AgentState
from .nodes import (
    router_node,
    study_node,
    interview_node,
    plan_node,
    crawler_node,
    chat_node,
)
try:
    from storage.conversation_store import ConversationStore
    from storage.models import Message
    HAS_CONVERSATION_STORE = True
except ImportError:
    HAS_CONVERSATION_STORE = False
    ConversationStore = None
    Message = None


def route_by_intent(state: AgentState) -> str:
    """根据意图路由到对应节点"""
    intent = state.get("intent", "chat")
    
    routing = {
        "study": "study",
        "interview": "interview",
        "crawl": "crawl",
        "plan": "plan",
        "chat": "chat",
    }
    
    return routing.get(intent, "chat")


def build_graph():
    """
    构建 Agent 工作流图
    
    流程：
    user_input → router → [study|interview|crawl|plan|chat] → response
    """
    # 创建状态图
    workflow = StateGraph(AgentState)
    
    # 添加节点
    workflow.add_node("router", router_node)
    workflow.add_node("study", study_node)
    workflow.add_node("interview", interview_node)
    workflow.add_node("crawl", crawler_node)
    workflow.add_node("plan", plan_node)
    workflow.add_node("chat", chat_node)
    
    # 设置入口
    workflow.set_entry_point("router")
    
    # 添加条件边（路由）
    workflow.add_conditional_edges(
        "router",
        route_by_intent,
        {
            "study": "study",
            "interview": "interview",
            "crawl": "crawl",
            "plan": "plan",
            "chat": "chat",
        }
    )
    
    # 所有处理节点都指向结束
    workflow.add_edge("study", END)
    workflow.add_edge("interview", END)
    workflow.add_edge("crawl", END)
    workflow.add_edge("plan", END)
    workflow.add_edge("chat", END)
    
    # 编译
    return workflow.compile()


# 全局实例
_graph = None

def get_graph():
    """获取图实例（单例）"""
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph


NODE_HANDLERS = {
    "study": study_node,
    "interview": interview_node,
    "crawl": crawler_node,
    "plan": plan_node,
    "chat": chat_node,
}


def run_agent_with_trace(
    user_input: str,
    progress_callback=None,
    conversation_history: list = None,
    session_id: str = ""
) -> dict:
    """
    运行 Agent（返回执行过程）

    Args:
        user_input: 用户输入
        progress_callback: 进度回调函数
        conversation_history: 对话历史，格式 [{"role": "user/assistant", "content": "..."}, ...]
        session_id: 会话标识

    Returns:
        {
            "response": str,
            "trace": list[dict],
            "state": AgentState,
            "updated_conversation_history": list,  # 更新后的对话历史
            "session_id": str,
        }
    """
    started = time.perf_counter()
    trace = []

    def add_event(step: str, detail: str):
        event = {
            "step": step,
            "detail": detail,
            "elapsed_ms": int((time.perf_counter() - started) * 1000),
        }
        trace.append(event)
        if progress_callback:
            progress_callback(event)

    # 初始化对话历史
    if conversation_history is None:
        conversation_history = []

    state = AgentState(
        user_input=user_input,
        intent="",
        conversation_history=conversation_history,
        session_id=session_id,
        memory_context={},
        rag_results=[],
        response="",
        should_update_memory=False,
    )

    add_event("开始", "接收用户输入")
    add_event("路由", "识别用户意图")
    state = router_node(state)

    intent = state.get("intent", "chat")
    node_name = route_by_intent(state)
    add_event("路由结果", f"命中意图：{intent}")
    add_event("执行", f"进入节点：{node_name}")

    handler = NODE_HANDLERS.get(node_name, chat_node)
    state = handler(state)

    if state.get("error"):
        add_event("异常", state.get("error", "未知错误"))
    else:
        add_event("完成", "已生成回复")

    # 更新对话历史（添加本轮对话）
    response = state.get("response", "抱歉，我没有理解你的意思。")
    updated_history = conversation_history.copy() if conversation_history else []

    # 添加用户输入和助手响应
    updated_history.append({"role": "user", "content": user_input})
    updated_history.append({"role": "assistant", "content": response})

    # 限制历史长度（保留最近100轮对话）
    max_history = 100
    if len(updated_history) > max_history * 2:  # 每轮包含user和assistant两条
        updated_history = updated_history[-(max_history * 2):]

    # 持久化对话到数据库（如果可用）
    if HAS_CONVERSATION_STORE and session_id:
        try:
            store = ConversationStore()

            # 查找或创建会话
            user_conversations = store.get_user_conversations(user_name="", limit=20)
            conversation = None
            for conv in user_conversations:
                if conv.session_id == session_id:
                    conversation = conv
                    break

            if not conversation:
                # 创建新会话
                conversation_id = store.create_conversation(
                    title="新对话",
                    user_name="",  # 暂时留空，未来可关联用户
                    session_id=session_id,
                    metadata={"created_from": "agent"}
                )
                conversation = store.get_conversation(conversation_id)

            # 计算响应时间
            response_time_ms = int((time.perf_counter() - started) * 1000)

            # 添加用户消息
            user_message = Message(
                id="",
                conversation_id=conversation.id,
                role="user",
                content=user_input,
                session_id=session_id,
                intent=state.get("intent", "chat"),
                response_time_ms=None,  # 用户消息无响应时间
                tokens_used=None,
                timestamp=datetime.now(),
                trace=[]
            )
            store.add_message(user_message)

            # 添加助手消息
            assistant_message = Message(
                id="",
                conversation_id=conversation.id,
                role="assistant",
                content=response,
                session_id=session_id,
                intent=state.get("intent", "chat"),
                response_time_ms=response_time_ms,
                tokens_used=None,  # 可以后续添加token计数
                timestamp=datetime.now(),
                trace=trace
            )
            store.add_message(assistant_message)
        except Exception as e:
            # 持久化失败不应影响主流程
            add_event("持久化警告", f"对话保存失败: {str(e)}")

    return {
        "response": response,
        "trace": trace,
        "state": state,
        "updated_conversation_history": updated_history,
        "session_id": session_id,
    }


def run_agent(user_input: str) -> str:
    """
    运行 Agent

    Args:
        user_input: 用户输入

    Returns:
        Agent 回复
    """
    result = run_agent_with_trace(
        user_input=user_input,
        conversation_history=[],
        session_id=""
    )
    return result["response"]
