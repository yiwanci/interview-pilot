"""
LangGraph 主流程图
"""
import time
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


def run_agent_with_trace(user_input: str, progress_callback=None) -> dict:
    """
    运行 Agent（返回执行过程）
    
    Returns:
        {
            "response": str,
            "trace": list[dict],
            "state": AgentState,
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

    state = AgentState(
        user_input=user_input,
        intent="",
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

    return {
        "response": state.get("response", "抱歉，我没有理解你的意思。"),
        "trace": trace,
        "state": state,
    }


def run_agent(user_input: str) -> str:
    """
    运行 Agent
    
    Args:
        user_input: 用户输入
    
    Returns:
        Agent 回复
    """
    result = run_agent_with_trace(user_input)
    return result["response"]
