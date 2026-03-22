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

# 统一 API Key（如果使用 codingplan 等聚合服务）
UNIFIED_API_KEY = os.getenv("UNIFIED_API_KEY", "")

LLM_CONFIGS = {
    "qwen": {
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "api_key": os.getenv("QWEN_API_KEY", UNIFIED_API_KEY),  # 优先用单独 Key，否则用统一 Key
        "model": "qwen3-max",
        "embedding_model": "text-embedding-v3",
    },
    "glm": {
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "api_key": os.getenv("GLM_API_KEY", UNIFIED_API_KEY),
        "model": "glm-4-flash",
        "embedding_model": "embedding-3",
    },
    "deepseek": {
        "base_url": "https://api.deepseek.com/v2",
        "api_key": os.getenv("DEEPSEEK_API_KEY", UNIFIED_API_KEY),
        "model": "deepseek-chat",
        "embedding_model": "deepseek-embedding",
    },
}

# 节点级 LLM 配置（从 .env 读取，默认全部使用 LLM_PROVIDER）
NODE_LLM_CONFIG = {
    "router": os.getenv("ROUTER_LLM_PROVIDER", LLM_PROVIDER),
    "study": os.getenv("STUDY_LLM_PROVIDER", LLM_PROVIDER),
    "interview": os.getenv("INTERVIEW_LLM_PROVIDER", LLM_PROVIDER),
    "plan": os.getenv("PLAN_LLM_PROVIDER", LLM_PROVIDER),
    "crawl": os.getenv("CRAWL_LLM_PROVIDER", LLM_PROVIDER),
    "chat": os.getenv("CHAT_LLM_PROVIDER", LLM_PROVIDER),
}

# 多模态大模型配置（用于图片识别、面经分析等）
MULTIMODAL_MODEL = os.getenv("MULTIMODAL_MODEL", "qwen-vl")

# 多模态大模型映射（支持视觉）
MULTIMODAL_CONFIGS = {
    "qwen-vl": {
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "api_key": os.getenv("QWEN_API_KEY", UNIFIED_API_KEY),
        "model": "qwen-vl-max",  # 多模态大模型，支持图片识别
    },
    "qwen-vl-plus": {
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "api_key": os.getenv("QWEN_API_KEY", UNIFIED_API_KEY),
        "model": "qwen-vl-plus-max",
    },
    "glm-4v": {
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "api_key": os.getenv("GLM_API_KEY", UNIFIED_API_KEY),
        "model": "glm-4v",
    },
}

def get_llm_config(node_name: str = None):
    """
    获取 LLM 配置，支持节点级别

    Args:
        node_name: 节点名称（router/study/interview/plan/crawl/chat）
                   如果为 None，使用全局 LLM_PROVIDER

    Returns:
        LLM 配置字典
    """
    # 如果指定节点，使用节点配置
    if node_name:
        provider = NODE_LLM_CONFIG.get(node_name, LLM_PROVIDER)
    else:
        provider = LLM_PROVIDER
    return LLM_CONFIGS.get(provider, LLM_CONFIGS["qwen"])

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

# 多模态大模型配置（用于图片识别、面经分析等）
MULTIMODAL_MODEL = os.getenv("MULTIMODAL_MODEL", "qwen-vl")

# 多模态大模型映射（支持视觉）
MULTIMODAL_CONFIGS = {
    "qwen-vl": {
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "api_keyser": os.getenv("QWEN_API_KEY", UNIFIED_API_KEY),
        "model": "qwen-vl-max",  # 多模态大模型，支持图片识别
    },
    "qwen-vl-plus": {
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "api_keyser": os.getenv("QWEN_API_KEY", UNIFIED_API_KEY),
        "model": "qwen-vl-plus-max",
    },
    "glm-4v": {
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "api_keyser": os.getenv("GLM_API_KEY", UNIFIED_API_KEY),
        "model": "glm-4v",
    },
}
