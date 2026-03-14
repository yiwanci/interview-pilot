"""
知识点分类体系
针对：Java后端 / AI Agent / 大模型算法
"""

KNOWLEDGE_SCHEMA = {
    "java_backend": {
        "name": "Java后端",
        "categories": {
            "java_basic": {
                "name": "Java基础",
                "tags": ["集合框架", "多线程", "JVM", "IO", "反射", "泛型"]
            },
            "spring": {
                "name": "Spring生态",
                "tags": ["IOC", "AOP", "SpringBoot", "SpringCloud", "MyBatis"]
            },
            "database": {
                "name": "数据库",
                "tags": ["MySQL", "索引", "事务", "Redis", "MongoDB"]
            },
            "middleware": {
                "name": "中间件",
                "tags": ["Kafka", "RabbitMQ", "Nginx", "Dubbo", "Zookeeper"]
            },
            "system_design": {
                "name": "系统设计",
                "tags": ["分布式", "微服务", "高并发", "缓存策略", "限流"]
            },
        }
    },
    "ai_agent": {
        "name": "AI Agent",
        "categories": {
            "llm_basic": {
                "name": "LLM基础",
                "tags": ["Prompt工程", "上下文管理", "Token", "温度参数"]
            },
            "rag": {
                "name": "RAG技术",
                "tags": ["向量检索", "Embedding", "分块策略", "重排序"]
            },
            "agent_framework": {
                "name": "Agent框架",
                "tags": ["LangChain", "LangGraph", "AutoGPT", "CrewAI"]
            },
            "memory": {
                "name": "记忆系统",
                "tags": ["长期记忆", "短期记忆", "对话管理", "Mem0"]
            },
            "tool_use": {
                "name": "工具调用",
                "tags": ["Function Calling", "MCP", "工具集成"]
            },
        }
    },
    "llm_algorithm": {
        "name": "大模型算法",
        "categories": {
            "transformer": {
                "name": "Transformer",
                "tags": ["注意力机制", "位置编码", "多头注意力", "FFN"]
            },
            "training": {
                "name": "训练技术",
                "tags": ["预训练", "SFT", "RLHF", "DPO", "PPO"]
            },
            "inference": {
                "name": "推理优化",
                "tags": ["量化", "KV Cache", "投机采样", "vLLM"]
            },
            "fine_tuning": {
                "name": "微调技术",
                "tags": ["LoRA", "QLoRA", "全量微调", "Adapter"]
            },
        }
    },
    "cs_basic": {
        "name": "计算机基础",
        "categories": {
            "algorithm": {
                "name": "算法",
                "tags": ["排序", "搜索", "动态规划", "图论", "贪心"]
            },
            "os": {
                "name": "操作系统",
                "tags": ["进程", "线程", "内存管理", "文件系统", "死锁"]
            },
            "network": {
                "name": "计算机网络",
                "tags": ["TCP", "UDP", "HTTP", "HTTPS", "DNS"]
            },
        }
    }
}

def get_all_domains():
    """获取所有领域"""
    return list(KNOWLEDGE_SCHEMA.keys())

def get_categories(domain: str):
    """获取某领域下的所有分类"""
    return list(KNOWLEDGE_SCHEMA.get(domain, {}).get("categories", {}).keys())

def get_tags(domain: str, category: str):
    """获取某分类下的所有标签"""
    return KNOWLEDGE_SCHEMA.get(domain, {}).get("categories", {}).get(category, {}).get("tags", [])
