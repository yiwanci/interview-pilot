"""
Streamlit 前端界面
"""
import streamlit as st
from datetime import date

# 设置页面必须在最前面
st.set_page_config(
    page_title="InterviewPilot - 面试准备助手",
    page_icon="🚀",
    layout="wide",
)

from agent import run_agent
from memory import MemoryManager
from storage import SQLiteStore


def init_session_state():
    """初始化 session state"""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "memory_manager" not in st.session_state:
        st.session_state.memory_manager = MemoryManager()
    if "db" not in st.session_state:
        st.session_state.db = SQLiteStore()


def render_sidebar():
    """渲染侧边栏"""
    with st.sidebar:
        st.title("🚀 InterviewPilot")
        st.caption("智能面试准备助手")
        
        st.divider()
        
        # 学习统计
        st.subheader("📊 学习统计")
        try:
            stats = st.session_state.db.get_stats()
            col1, col2 = st.columns(2)
            with col1:
                st.metric("知识点", stats.get("total_knowledge_points", 0))
            with col2:
                st.metric("已掌握", stats.get("mastered_count", 0))
            
            due_count = stats.get("due_review_count", 0)
            if due_count > 0:
                st.warning(f"⏰ 有 {due_count} 个知识点待复习")
        except Exception:
            st.info("暂无学习数据")
        
        st.divider()
        
        # 快捷操作
        st.subheader("⚡ 快捷操作")
        
        if st.button("📝 开始模拟面试", use_container_width=True):
            add_user_message("考考我")
        
        if st.button("📅 查看今日计划", use_container_width=True):
            add_user_message("今天学什么")
        
        if st.button("📊 查看周报", use_container_width=True):
            add_user_message("本周学习周报")
        
        st.divider()
        
        # 用户设置
        st.subheader("⚙️ 用户设置")
        with st.expander("设置目标"):
            positions = st.multiselect(
                "目标岗位",
                ["Java后端", "AI Agent开发", "大模型算法", "前端开发", "全栈开发"],
                default=[]
            )
            companies = st.text_input("目标公司（逗号分隔）", "")
            
            if st.button("保存设置"):
                try:
                    mm = st.session_state.memory_manager
                    if positions:
                        mm.set_user_profile(target_positions=positions)
                    if companies:
                        company_list = [c.strip() for c in companies.split(",") if c.strip()]
                        mm.set_user_profile(target_companies=company_list)
                    st.success("设置已保存！")
                except Exception as e:
                    st.error(f"保存失败：{e}")
        
        st.divider()
        
        # 使用说明
        with st.expander("📖 使用说明"):
            st.markdown("""
            **学习知识**
            - 输入「讲讲 Redis 持久化」
            - 输入「什么是 JVM 垃圾回收」
            
            **模拟面试**
            - 输入「考考我」开始
            - 回答后会自动评分
            
            **学习计划**
            - 输入「今天学什么」
            - 输入「本周周报」
            
            **搜集面经**
            - 输入「搜集小红书 Java 面经」
            - 输入「抓取字节 LeetCode 题」
            """)


def add_user_message(content: str):
    """添加用户消息并处理"""
    st.session_state.messages.append({
        "role": "user",
        "content": content
    })
    
    # 调用 Agent
    with st.spinner("思考中..."):
        try:
            response = run_agent(content)
        except Exception as e:
            response = f"抱歉，处理时出错了：{e}"
    
    st.session_state.messages.append({
        "role": "assistant",
        "content": response
    })
    
    st.rerun()


def render_chat():
    """渲染聊天界面"""
    st.title("💬 对话")
    
    # 显示历史消息
    for message in st.session_state.messages:
        role = message["role"]
        content = message["content"]
        
        if role == "user":
            with st.chat_message("user"):
                st.write(content)
        else:
            with st.chat_message("assistant"):
                st.write(content)
    
    # 输入框
    if prompt := st.chat_input("输入消息...（试试「考考我」或「讲讲 Redis」）"):
        add_user_message(prompt)


def render_knowledge_tab():
    """渲染知识库标签页"""
    st.subheader("📚 我的知识库")
    
    try:
        db = st.session_state.db
        
        # 筛选
        col1, col2 = st.columns(2)
        with col1:
            domain_filter = st.selectbox(
                "领域筛选",
                ["全部", "java_backend", "ai_agent", "llm_algorithm", "cs_basic"]
            )
        with col2:
            sort_by = st.selectbox(
                "排序方式",
                ["掌握度（低→高）", "掌握度（高→低）", "最近复习"]
            )
        
        # 获取知识点
        domain = None if domain_filter == "全部" else domain_filter
        knowledge_points = db.get_all_knowledge_points(domain=domain)
        
        if not knowledge_points:
            st.info("暂无知识点，开始学习后会自动添加。")
            return
        
        # 排序
        if "低→高" in sort_by:
            knowledge_points.sort(key=lambda x: x.mastery_level)
        elif "高→低" in sort_by:
            knowledge_points.sort(key=lambda x: x.mastery_level, reverse=True)
        
        # 显示
        for kp in knowledge_points:
            with st.expander(f"{kp.name} - {kp.mastery_level:.0%}"):
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.write(f"**领域**: {kp.domain}")
                with col2:
                    st.write(f"**分类**: {kp.category}")
                with col3:
                    st.write(f"**复习次数**: {kp.repetitions}")
                
                # 进度条
                st.progress(kp.mastery_level, text=f"掌握程度: {kp.mastery_level:.0%}")
                
                # 下次复习
                if kp.next_review_at:
                    st.caption(f"下次复习: {kp.next_review_at}")
                
                # 操作按钮
                if st.button(f"复习「{kp.name}」", key=f"review_{kp.id}"):
                    add_user_message(f"讲讲 {kp.name}")
    
    except Exception as e:
        st.error(f"加载知识库失败：{e}")


def render_import_tab():
    """渲染导入标签页"""
    st.subheader("📥 导入面经")
    
    st.markdown("""
    ### 方式一：直接粘贴
    将面经内容粘贴到下方文本框，点击导入。
    """)
    
    content = st.text_area("面经内容", height=200, placeholder="粘贴面经内容...")
    title = st.text_input("标题（可选）", placeholder="如：字节跳动一面")
    
    if st.button("导入", type="primary"):
        if content:
            add_user_message(f"导入面经：{title or '手动导入'}\n\n{content}")
        else:
            st.warning("请输入面经内容")
    
    st.divider()
    
    st.markdown("""
    ### 方式二：使用爬虫
    在对话框输入指令，如：
    - 「搜集小红书 Java 面经」
    - 「抓取字节 LeetCode 题」
    
    ### 方式三：MediaCrawler
    使用 [MediaCrawler](https://github.com/NanmiCoder/MediaCrawler) 工具爬取小红书/抖音数据，
    导出 JSON 后放到 `data/raw/` 目录。
    """)


def main():
    """主函数"""
    init_session_state()
    
    # 侧边栏
    render_sidebar()
    
    # 主内容区 - 标签页
    tab1, tab2, tab3 = st.tabs(["💬 对话", "📚 知识库", "📥 导入"])
    
    with tab1:
        render_chat()
    
    with tab2:
        render_knowledge_tab()
    
    with tab3:
        render_import_tab()


if __name__ == "__main__":
    main()
