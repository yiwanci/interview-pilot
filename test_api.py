"""
API 连接测试
用于验证 LLM API 配置是否正确
测试完成后可删除此文件
"""
import sys
from pathlib import Path

# 确保项目根目录在路径中
ROOT_DIR = Path(__file__).parent
sys.path.insert(0, str(ROOT_DIR))

from openai import OpenAI
from config import get_llm_config


def test_llm_api():
    """测试 LLM API"""
    print("=" * 50)
    print("🔍 测试 LLM API 连接")
    print("=" * 50)
    
    config = get_llm_config()
    print(f"Provider: {config.get('model', 'unknown')}")
    print(f"Base URL: {config.get('base_url', 'unknown')}")
    print(f"API Key: {config.get('api_key', '')[:10]}..." if config.get('api_key') else "API Key: 未设置")
    print()
    
    try:
        client = OpenAI(
            api_key=config["api_key"],
            base_url=config["base_url"],
        )
        
        print("📤 发送测试请求...")
        response = client.chat.completions.create(
            model=config["model"],
            messages=[{"role": "user", "content": "你好，请回复'API连接正常'"}],
            max_tokens=50,
        )
        
        result = response.choices[0].message.content
        print(f"📥 响应: {result}")
        print()
        print("✅ LLM API 连接正常！")
        return True
        
    except Exception as e:
        print(f"❌ LLM API 连接失败: {e}")
        return False


def test_embedding_api():
    """测试 Embedding API"""
    print()
    print("=" * 50)
    print("🔍 测试 Embedding API 连接")
    print("=" * 50)
    
    config = get_llm_config()
    embedding_model = config.get("embedding_model", "")
    print(f"Embedding Model: {embedding_model}")
    print()
    
    try:
        client = OpenAI(
            api_key=config["api_key"],
            base_url=config["base_url"],
        )
        
        print("📤 发送测试请求...")
        response = client.embeddings.create(
            model=embedding_model,
            input=["测试文本"],
        )
        
        embedding = response.data[0].embedding
        print(f"📥 向量维度: {len(embedding)}")
        print(f"📥 向量前5维: {embedding[:5]}")
        print()
        print("✅ Embedding API 连接正常！")
        return True
        
    except Exception as e:
        print(f"❌ Embedding API 连接失败: {e}")
        return False


def main():
    """主函数"""
    print()
    print("🚀 InterviewPilot API 测试")
    print()
    
    llm_ok = test_llm_api()
    embed_ok = test_embedding_api()
    
    print()
    print("=" * 50)
    print("📋 测试结果汇总")
    print("=" * 50)
    print(f"LLM API:       {'✅ 正常' if llm_ok else '❌ 失败'}")
    print(f"Embedding API: {'✅ 正常' if embed_ok else '❌ 失败'}")
    print()
    
    if llm_ok and embed_ok:
        print("🎉 所有 API 测试通过，可以正常使用！")
        print()
        print("下一步：")
        print("  1. 启动 Qdrant: docker-compose up -d")
        print("  2. 运行应用: python main.py")
    else:
        print("⚠️ 部分 API 测试失败，请检查 .env 配置")
        print()
        print("检查项：")
        print("  1. .env 文件中 LLM_PROVIDER 是否正确")
        print("  2. 对应的 API_KEY 是否已填写")
        print("  3. API Key 是否有效且有余额")


if __name__ == "__main__":
    main()
