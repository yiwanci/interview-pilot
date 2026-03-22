"""
多模态大模型配置
支持 qwen-vl、glm-4v 等多模态模型
"""
import os
from dotenv import load_dotenv

load_dotenv()

# 统一 API Key
UNIFIED_API_KEY = os.getenv("UNIFIED_API_KEY", "")

# 多模态大模型映射（支持视觉模型）
MULTIMODAL_CONFIGS = {
    "qwen-vl": {
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "api_key": os.getenv("QWEN_API_KEY", UNIFIED_API_KEY),
        "model": "qwen-vl-max",
    },
    "qwen-vl-plus": {
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "api_key": os.getenv("QWEN_API_KEY", UNIFIED_API_KEY),
        "model": "qwen-vl-plus",
    },
    "glm-4v": {
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "api_key": os.getenv("GLM_API_KEY", UNIFIED_API_KEY),
        "model": "glm-4v",
    },
}

# 环境变量配置
MULTIMODAL_MODEL = os.getenv("MULTIMODAL_MODEL", "qwen-vl")


def get_multimodal_config(model_name: str = None) -> dict:
    """
    获取多模态大模型配置

    Args:
        model_name: 模型名称（如 qwen-vl），如果为 None 使用环境变量 MULTIMODAL_MODEL

    Returns:
        模型配置字典
    """
    if not model_name:
        model_name = MULTIMODAL_MODEL

    return MULTIMODAL_CONFIGS.get(model_name, MULTIMODAL_CONFIGS["qwen-vl"])


def is_multimodal_available() -> bool:
    """检查多模态大模型是否可用"""
    model_name = MULTIMODAL_MODEL
    return model_name in MULTIMODAL_CONFIGS and MULTIMODAL_CONFIGS[model_name].get("api_key")
