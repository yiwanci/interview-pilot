"""
LangGraph 主流程图
"""
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


def run_agent(user_input: str) -> str:
    """
    运行 Agent
    
    Args:
        user_input: 用户输入
    
    Returns:
        Agent 回复
    """
    graph = get_graph()
    
    initial_state = AgentState(
        user_input=user_input,
        intent="",
        memory_context={},
        rag_results=[],
        response="",
        should_update_memory=False,
    )
    
    # 运行图
    result = graph.invoke(initial_state)
    
    return result.get("response", "抱歉，我没有理解你的意思。")
