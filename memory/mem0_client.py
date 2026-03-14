"""
Mem0 客户端封装
处理语义记忆的存取
"""
from typing import Optional
from mem0 import Memory

from config import get_mem0_config


class Mem0Client:
    """
    Mem0 语义记忆客户端
    
    用途：存储非结构化的"软性记忆"
    - 用户对某知识点的理解程度描述
    - 学习过程中的反馈和感受
    - 用户偏好和习惯
    
    使用示例:
        client = Mem0Client()
        client.add("用户对Redis RDB理解不深，混淆了触发机制", category="knowledge")
        results = client.search("Redis掌握情况")
    """
    
    DEFAULT_USER_ID = "default_user"
    
    def __init__(self, user_id: str = None):
        self.user_id = user_id or self.DEFAULT_USER_ID
        self._memory = None
    
    @property
    def memory(self) -> Memory:
        """懒加载 Mem0 实例"""
        if self._memory is None:
            config = get_mem0_config()
            try:
                self._memory = Memory.from_config(config)
            except TypeError as e:
                if "dimensions" not in str(e):
                    raise
                embed_config = config.get("embedder", {}).get("config", {})
                embed_config.pop("dimensions", None)
                self._memory = Memory.from_config(config)
        return self._memory
    
    def add(
        self,
        text: str,
        category: str = "general",
        metadata: dict = None,
    ) -> dict:
        """
        添加记忆
        
        Args:
            text: 记忆内容（自然语言描述）
            category: 分类 (knowledge/preference/feedback/plan)
            metadata: 额外元数据
        
        Returns:
            添加结果
        """
        meta = metadata or {}
        meta["category"] = category
        
        try:
            result = self.memory.add(
                text,
                user_id=self.user_id,
                metadata=meta,
            )
            return result
        except Exception as e:
            if self._is_dimension_error(e):
                return {}
            raise
    
    def search(
        self,
        query: str,
        top_k: int = 5,
        category: str = None,
    ) -> list[dict]:
        """
        搜索记忆
        
        Args:
            query: 搜索query（自然语言）
            top_k: 返回数量
            category: 过滤分类
        
        Returns:
            相关记忆列表
        """
        try:
            results = self.memory.search(
                query,
                user_id=self.user_id,
                limit=top_k,
            )
        except Exception as e:
            if self._is_dimension_error(e):
                return []
            raise
        
        # 过滤分类
        if category:
            results = [
                r for r in results
                if r.get("metadata", {}).get("category") == category
            ]
        
        return results
    
    def get_all(self, category: str = None) -> list[dict]:
        """获取所有记忆"""
        try:
            results = self.memory.get_all(user_id=self.user_id)
        except Exception as e:
            if self._is_dimension_error(e):
                return []
            raise
        
        if category:
            results = [
                r for r in results
                if r.get("metadata", {}).get("category") == category
            ]
        
        return results
    
    def update(self, memory_id: str, text: str) -> dict:
        """更新记忆"""
        return self.memory.update(memory_id, text)
    
    def delete(self, memory_id: str):
        """删除记忆"""
        self.memory.delete(memory_id)
    
    def delete_all(self):
        """删除所有记忆（谨慎使用）"""
        self.memory.delete_all(user_id=self.user_id)
    
    # ============ 便捷方法 ============
    
    def add_knowledge_feedback(self, knowledge_name: str, feedback: str):
        """添加知识点学习反馈"""
        text = f"关于「{knowledge_name}」：{feedback}"
        return self.add(text, category="knowledge")
    
    def add_preference(self, preference: str):
        """添加用户偏好"""
        return self.add(preference, category="preference")
    
    def add_study_summary(self, date: str, summary: str):
        """添加学习总结"""
        text = f"{date} 学习总结：{summary}"
        return self.add(text, category="summary", metadata={"date": date})
    
    def get_knowledge_context(self, topic: str) -> str:
        """
        获取某主题相关的记忆上下文
        用于给 Agent 提供背景信息
        """
        memories = self.search(topic, top_k=5, category="knowledge")
        
        if not memories:
            return ""
        
        context_parts = []
        for m in memories:
            memory_text = m.get("memory", "")
            if memory_text:
                context_parts.append(f"- {memory_text}")
        
        return "\n".join(context_parts)

    @staticmethod
    def _is_dimension_error(error: Exception) -> bool:
        msg = str(error).lower()
        return (
            "dimension for embedding v3 is invalid" in msg
            or "invalidparameter" in msg
            or "parameters.dimension" in msg
        )
