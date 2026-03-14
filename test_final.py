#!/usr/bin/env python
"""
最终功能测试
"""
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).parent
sys.path.insert(0, str(ROOT_DIR))

def test_intents():
    """测试不同意图"""
    from agent.graph import run_agent

    test_cases = [
        ("考考我", "interview"),
        ("讲讲 Redis", "study"),
        ("今天学什么", "plan"),
        ("帮我爬取 LeetCode 题目", "crawl"),
        ("你好", "chat"),
    ]

    for query, expected_intent in test_cases:
        print(f"\n测试: '{query}'")
        try:
            response = run_agent(query)
            print(f"  响应长度: {len(response)} 字符")
            print(f"  预览: {response[:100]}...")
        except Exception as e:
            print(f"  错误: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            return False

    return True

if __name__ == "__main__":
    print("=== InterviewPilot 功能测试 ===")
    success = test_intents()
    if success:
        print("\n✅ 所有测试通过")
    else:
        print("\n❌ 测试失败")
    sys.exit(0 if success else 1)