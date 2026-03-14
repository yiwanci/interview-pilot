"""
Qdrant 向量数据库操作
"""
import uuid
from typing import Optional
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct,
    Filter, FieldCondition, MatchValue
)

from config import QDRANT_HOST, QDRANT_PORT, QDRANT_COLLECTION
from .models import DocumentChunk


class VectorStore:
    def __init__(self, collection_name: str = None, vector_size: int = 1536):
        self.client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
        self.collection_name = collection_name or QDRANT_COLLECTION
        self.vector_size = vector_size
        self._ensure_collection()
    
    def _ensure_collection(self):
        """确保collection存在"""
        collections = [c.name for c in self.client.get_collections().collections]
        if self.collection_name not in collections:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.vector_size,
                    distance=Distance.COSINE
                )
            )
    
    def add_documents(self, chunks: list[DocumentChunk]):
        """添加文档"""
        if not chunks:
            return
        
        points = []
        for chunk in chunks:
            if not chunk.embedding:
                continue
            
            if not chunk.id:
                chunk.id = str(uuid.uuid4())
            
            points.append(PointStruct(
                id=chunk.id,
                vector=chunk.embedding,
                payload={
                    "doc_id": chunk.doc_id,
                    "content": chunk.content,
                    "chunk_type": chunk.chunk_type,
                    "source": chunk.source,
                    "domain": chunk.domain,
                    "category": chunk.category,
                    "tags": chunk.tags,
                    "question": chunk.question,
                    "answer": chunk.answer,
                    "company": chunk.company,
                    "position": chunk.position,
                }
            ))
        
        if points:
            self.client.upsert(
                collection_name=self.collection_name,
                points=points
            )
    
    def search(
        self,
        query_vector: list[float],
        top_k: int = 10,
        domain: str = None,
        source: str = None,
    ) -> list[DocumentChunk]:
        """向量搜索"""
        
        # 构建过滤条件
        filters = []
        if domain:
            filters.append(FieldCondition(key="domain", match=MatchValue(value=domain)))
        if source:
            filters.append(FieldCondition(key="source", match=MatchValue(value=source)))
        
        search_filter = Filter(must=filters) if filters else None
        
        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            limit=top_k,
            query_filter=search_filter,
        )
        
        chunks = []
        for r in results:
            payload = r.payload
            chunks.append(DocumentChunk(
                id=str(r.id),
                doc_id=payload.get("doc_id", ""),
                content=payload.get("content", ""),
                chunk_type=payload.get("chunk_type", "text"),
                source=payload.get("source", ""),
                domain=payload.get("domain", ""),
                category=payload.get("category", ""),
                tags=payload.get("tags", []),
                question=payload.get("question", ""),
                answer=payload.get("answer", ""),
                company=payload.get("company", ""),
                position=payload.get("position", ""),
            ))
        
        return chunks
    
    def delete_by_doc_id(self, doc_id: str):
        """根据原始文档ID删除所有分块"""
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=Filter(
                must=[FieldCondition(key="doc_id", match=MatchValue(value=doc_id))]
            )
        )
    
    def get_collection_info(self) -> dict:
        """获取collection信息"""
        info = self.client.get_collection(self.collection_name)
        return {
            "name": self.collection_name,
            "vectors_count": info.vectors_count,
            "points_count": info.points_count,
        }
