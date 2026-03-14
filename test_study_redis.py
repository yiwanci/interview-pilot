import os
import sys
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent
sys.path.insert(0, str(ROOT_DIR))

load_dotenv()

print("=== 测试 '讲讲 Redis' 完整流程 ===")

# 导入所需模块
from config import get_llm_config
from openai import OpenAI
from agent.prompts.study_prompt import TOPIC_EXTRACT_PROMPT

config = get_llm_config()
print(f"LLM Provider: {os.getenv('LLM_PROVIDER')}")
print(f"Model: {config['model']}")

client = OpenAI(
    api_key=config["api_key"],
    base_url=config["base_url"],
)

# 1. 测试主题提取
print("\n1. 测试主题提取...")
user_input = "讲讲 Redis"
prompt = TOPIC_EXTRACT_PROMPT.format(user_input=user_input)
print(f"Prompt: {prompt[:100]}...")

try:
    response = client.chat.completions.create(
        model=config["model"],
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=50,
    )
    topic = response.choices[0].message.content.strip()
    print(f"✓ 主题提取成功: '{topic}'")
except Exception as e:
    print(f"✗ 主题提取失败: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

# 2. 测试 memory manager
print("\n2. 测试 MemoryManager...")
try:
    from memory import MemoryManager
    mm = MemoryManager()
    memory_context = mm.format_context_for_prompt("Redis")
    print(f"✓ MemoryManager 成功，上下文长度: {len(memory_context)}")
except Exception as e:
    print(f"✗ MemoryManager 失败: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

# 3. 测试 RAG
print("\n3. 测试 RAG Pipeline...")
try:
    from rag import RAGPipeline
    rag = RAGPipeline()
    print("✓ RAGPipeline 创建成功")

    # 简单的检索测试
    results = rag.retrieve("Redis", top_k=2)
    print(f"  检索到 {len(results)} 个结果")

    # 查询测试
    if results:
        answer = rag.query("Redis是什么", top_k=2)
        print(f"  RAG 查询成功，回答长度: {len(answer.get('answer', ''))}")
    else:
        print("  ⚠️ 无检索结果（可能是向量数据库为空）")

except Exception as e:
    print(f"✗ RAG 失败: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

# 4. 测试完整的学习节点
print("\n4. 测试完整 StudyNode...")
try:
    from agent.nodes.study_node import StudyNode
    node = StudyNode()
    print("✓ StudyNode 创建成功")

    # 模拟状态
    test_state = {"user_input": "讲讲 Redis"}
    result_state = node(test_state)

    if "error" in result_state:
        print(f"✗ StudyNode 返回错误: {result_state['error']}")
    else:
        response = result_state.get("response", "")
        print(f"✓ StudyNode 成功，响应长度: {len(response)}")
        print(f"  响应预览: {response[:200]}...")

except Exception as e:
    print(f"✗ StudyNode 失败: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

print("\n=== 测试完成 ===")