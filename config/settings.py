"""
全局配置
使用 .env 文件管理敏感信息
"""
# 在文件开头的 import 之后，添加导出

# ... 其他代码保持不变

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# 项目根目录
BASE_DIR = Path(__file__).parent.parent

# 数据目录
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

# SQLite
SQLITE_DB_PATH = DATA_DIR / "interview_pilot.db"

# Qdrant
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", 6333))
QDRANT_COLLECTION = "interview_pilot"

# LLM 配置（国产API，兼容OpenAI接口）
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "qwen")  # qwen / glm / deepseek

LLM_CONFIGS = {
    "qwen": {
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "api_key": os.getenv("QWEN_API_KEY", ""),
        "model": "qwen3-max",
        "embedding_model": "text-embedding-v3",
    },
    "glm": {
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "api_key": os.getenv("GLM_API_KEY", ""),
        "model": "glm-4-flash",
        "embedding_model": "embedding-3",
    },
    "deepseek": {
        "base_url": "https://api.deepseek.com/v2",
        "api_key": os.getenv("DEEPSEEK_API_KEY", ""),
        "model": "deepseek-chat",
        "embedding_model": "deepseek-embedding",},
}

def get_llm_config():
    """获取当前LLM配置"""
    return LLM_CONFIGS.get(LLM_PROVIDER, LLM_CONFIGS["qwen"])

# Mem0 配置
def get_mem0_config():
    llm_cfg = get_llm_config()

    # 根据 provider 设置 embedding 维度
    provider = LLM_PROVIDER
    embed_config = {
        "model": llm_cfg["embedding_model"],
        "api_key": llm_cfg["api_key"],
        "openai_base_url": llm_cfg["base_url"],
    }

    # 通义千问 embedding v3 需要指定维度
    if provider == "qwen" and "v3" in llm_cfg["embedding_model"]:
        embed_config["dimensions"] = 1024

    return {
        "llm": {
            "provider": "openai",
            "config": {
                "model": llm_cfg["model"],
                "api_key": llm_cfg["api_key"],
                "openai_base_url": llm_cfg["base_url"],
            }
        },
        "embedder": {
            "provider": "openai",
            "config": embed_config,
        },
        "vector_store": {
            "provider": "qdrant",
            "config": {
                "host": QDRANT_HOST,
                "port": QDRANT_PORT,
                "collection_name": f"{QDRANT_COLLECTION}_memory",
            }
        }
    }
