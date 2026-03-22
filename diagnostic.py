#!/usr/bin/env python
"""
诊断脚本 - 检查系统问题
"""
import sys
import os
import traceback

sys.path.insert(0, '.')

print("=== 系统诊断 ===")
print(f"Python: {sys.executable}")
print(f"工作目录: {os.getcwd()}")
print(f"Python路径: {sys.path[:3]}")

# 1. 检查基本导入
print("\n--- 1. 检查基本导入 ---")
modules_to_test = [
    ("streamlit", "streamlit"),
    ("openai", "OpenAI"),
    ("langgraph", "StateGraph"),
    ("qdrant_client", "QdrantClient"),
    ("mem0ai", "Mem0"),
]

for module_name, attr_name in modules_to_test:
    try:
        module = __import__(module_name)
        print(f"[OK] {module_name} 导入成功")
    except ImportError as e:
        print(f"[MISSING] {module_name} 导入失败: {e}")

# 2. 检查项目模块导入
print("\n--- 2. 检查项目模块导入 ---")
project_modules = [
    ("config", "get_llm_config"),
    ("agent", "run_agent_with_trace"),
    ("agent.state", "AgentState"),
    ("agent.nodes.router_node", "router_node"),
    ("agent.nodes.study_node", "StudyNode"),
    ("agent.nodes.interview_node", "InterviewNode"),
    ("memory", "MemoryManager"),
    ("storage", "SQLiteStore"),
    ("storage.conversation_store", "ConversationStore"),
]

for module_path, attr_name in project_modules:
    try:
        if '.' in module_path:
            # 处理子模块导入
            parts = module_path.split('.')
            module = __import__(parts[0])
            for part in parts[1:]:
                module = getattr(module, part)
            print(f"[OK] {module_path} 导入成功")
        else:
            __import__(module_path)
            print(f"[OK] {module_path} 导入成功")
    except Exception as e:
        print(f"[ERROR] {module_path} 导入失败: {e}")
        traceback.print_exc()

# 3. 检查配置
print("\n--- 3. 检查配置 ---")
try:
    from config import get_llm_config
    config = get_llm_config()
    print(f"[OK] LLM配置加载成功")
    print(f"    Provider: {os.getenv('LLM_PROVIDER', 'qwen')}")
    print(f"    Model: {config.get('model', 'N/A')}")
    print(f"    Base URL: {config.get('base_url', 'N/A')}")
    print(f"    API Key: {config.get('api_key', 'N/A')[:10]}...")
except Exception as e:
    print(f"[ERROR] 配置加载失败: {e}")

# 4. 测试数据库连接
print("\n--- 4. 测试数据库连接 ---")
try:
    from storage import SQLiteStore
    db = SQLiteStore()
    stats = db.get_stats()
    print(f"[OK] SQLite数据库连接成功")
    print(f"    知识点总数: {stats.get('total_knowledge_points', 0)}")
    print(f"    学习日志数: {stats.get('total_study_logs', 0)}")
except Exception as e:
    print(f"[ERROR] 数据库连接失败: {e}")

# 5. 测试对话存储
print("\n--- 5. 测试对话存储 ---")
try:
    from storage.conversation_store import ConversationStore
    store = ConversationStore()
    print(f"[OK] ConversationStore初始化成功")

    # 测试创建会话
    import uuid
    from datetime import datetime
    from storage.models import Message

    session_id = f"test_diag_{int(datetime.now().timestamp())}"
    conv_id = store.create_conversation(
        title="诊断测试",
        session_id=session_id
    )
    print(f"[OK] 创建会话成功: {conv_id}")

    # 测试添加消息
    msg = Message(
        id=str(uuid.uuid4()),
        conversation_id=conv_id,
        role="user",
        content="诊断测试消息"
    )
    store.add_message(msg)
    print(f"[OK] 添加消息成功")

    # 清理
    store.delete_conversation(conv_id)
    print(f"[OK] 清理测试数据")

except Exception as e:
    print(f"[ERROR] 对话存储测试失败: {e}")
    traceback.print_exc()

# 6. 测试Agent初始化（不使用实际API调用）
print("\n--- 6. 测试Agent初始化 ---")
try:
    from unittest.mock import Mock, patch

    # Mock OpenAI调用
    with patch('openai.OpenAI') as mock_openai:
        mock_client = Mock()
        mock_openai.return_value = mock_client

        # Mock API响应
        mock_response = Mock()
        mock_response.choices[0].message.content = "mocked response"
        mock_client.chat.completions.create.return_value = mock_response

        # 尝试运行agent
        from agent import run_agent_with_trace

        result = run_agent_with_trace(
            user_input="测试输入",
            conversation_history=[],
            session_id="test_session"
        )

        print(f"[OK] Agent初始化成功")
        print(f"    响应: {result.get('response', 'N/A')[:50]}...")

except Exception as e:
    print(f"[ERROR] Agent测试失败: {e}")
    traceback.print_exc()

print("\n=== 诊断完成 ===")
print("总结：")
print("1. 检查缺失的依赖包")
print("2. 修复导入错误")
print("3. 检查配置文件")
print("4. 测试数据库连接")
print("5. 测试Agent流程")