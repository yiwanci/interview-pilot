"""
对话会话存储
管理会话和消息的持久化
"""
import sqlite3
import json
import uuid
from datetime import datetime
from typing import Optional, List
from contextlib import contextmanager

from config import SQLITE_DB_PATH
from .models import Conversation, Message


def _parse_datetime(dt_str: Optional[str]) -> Optional[datetime]:
    """解析datetime字符串，支持多种格式"""
    if not dt_str:
        return None

    # 尝试ISO格式
    try:
        return datetime.fromisoformat(dt_str)
    except (ValueError, AttributeError):
        pass

    # 尝试SQLite格式 (YYYY-MM-DD HH:MM:SS)
    try:
        return datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
    except (ValueError, AttributeError):
        pass

    # 尝试其他常见格式
    formats = [
        "%Y-%m-%dT%H:%M:%S",  # ISO without microseconds
        "%Y-%m-%dT%H:%M:%S.%f",  # ISO with microseconds
        "%Y-%m-%d %H:%M:%S.%f",  # SQLite with microseconds
    ]

    for fmt in formats:
        try:
            return datetime.strptime(dt_str, fmt)
        except (ValueError, AttributeError):
            continue

    # 如果都无法解析，返回None
    return None


class ConversationStore:
    """对话会话存储管理"""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or SQLITE_DB_PATH
        self._init_tables()

    @contextmanager
    def _get_conn(self):
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_tables(self):
        """初始化会话表结构"""
        with self._get_conn() as conn:
            conn.executescript("""
                -- 会话表
                CREATE TABLE IF NOT EXISTS conversations (
                    id              TEXT PRIMARY KEY,
                    title           TEXT NOT NULL DEFAULT '新对话',
                    user_name       TEXT DEFAULT '',
                    session_id      TEXT DEFAULT '',
                    metadata        TEXT DEFAULT '{}',
                    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    message_count   INTEGER DEFAULT 0,
                    last_message    TEXT
                );

                -- 消息表
                CREATE TABLE IF NOT EXISTS messages (
                    id              TEXT PRIMARY KEY,
                    conversation_id TEXT NOT NULL,
                    role            TEXT NOT NULL,  -- 'user' or 'assistant'
                    content         TEXT NOT NULL,
                    timestamp       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    session_id      TEXT DEFAULT '',
                    intent          TEXT DEFAULT '',  -- study/interview/plan/chat/crawl
                    response_time_ms INTEGER,
                    tokens_used     INTEGER,
                    trace           TEXT DEFAULT '[]',
                    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
                );

                -- 创建索引
                CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversations(user_name);
                CREATE INDEX IF NOT EXISTS idx_conversations_updated ON conversations(updated_at DESC);
                CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id);
                CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp DESC);
            """)

    # ============ 会话操作 ============

    def create_conversation(self, title: str = "新对话", user_name: str = "",
                          session_id: str = "", metadata: dict = None) -> str:
        """
        创建新会话

        Args:
            title: 会话标题
            user_name: 用户名
            session_id: 会话标识
            metadata: 额外元数据

        Returns:
            会话ID
        """
        conversation_id = str(uuid.uuid4())
        now = datetime.now()
        now_iso = now.isoformat()

        with self._get_conn() as conn:
            conn.execute("""
                INSERT INTO conversations
                (id, title, user_name, session_id, metadata, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                conversation_id, title, user_name, session_id,
                json.dumps(metadata or {}, ensure_ascii=False),
                now_iso, now_iso
            ))

        return conversation_id

    def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """获取会话详情"""
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM conversations WHERE id = ?", (conversation_id,)
            ).fetchone()

        if row:
            return self._row_to_conversation(row)
        return None

    def update_conversation(self, conversation: Conversation):
        """更新会话信息"""
        with self._get_conn() as conn:
            conn.execute("""
                UPDATE conversations SET
                    title = ?, user_name = ?, session_id = ?,
                    metadata = ?, updated_at = ?, message_count = ?,
                    last_message = ?
                WHERE id = ?
            """, (
                conversation.title,
                conversation.user_name,
                conversation.session_id,
                json.dumps(conversation.metadata, ensure_ascii=False),
                conversation.updated_at,
                conversation.message_count,
                conversation.last_message,
                conversation.id
            ))

    def delete_conversation(self, conversation_id: str):
        """删除会话（级联删除消息）"""
        with self._get_conn() as conn:
            conn.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))

    def get_user_conversations(self, user_name: str = "", limit: int = 50) -> List[Conversation]:
        """
        获取用户的会话列表

        Args:
            user_name: 用户名（空字符串表示所有用户）
            limit: 返回数量

        Returns:
            会话列表（按更新时间倒序）
        """
        with self._get_conn() as conn:
            if user_name:
                rows = conn.execute("""
                    SELECT * FROM conversations
                    WHERE user_name = ?
                    ORDER BY updated_at DESC
                    LIMIT ?
                """, (user_name, limit)).fetchall()
            else:
                rows = conn.execute("""
                    SELECT * FROM conversations
                    ORDER BY updated_at DESC
                    LIMIT ?
                """, (limit,)).fetchall()

        return [self._row_to_conversation(r) for r in rows]

    def get_recent_conversations(self, days: int = 7) -> List[Conversation]:
        """获取最近N天的会话"""
        with self._get_conn() as conn:
            rows = conn.execute("""
                SELECT * FROM conversations
                WHERE updated_at > datetime('now', ?)
                ORDER BY updated_at DESC
            """, (f"-{days} days",)).fetchall()

        return [self._row_to_conversation(r) for r in rows]

    # ============ 消息操作 ============

    def add_message(self, message: Message) -> str:
        """
        添加消息并更新会话统计

        Args:
            message: 消息对象

        Returns:
            消息ID
        """
        if not message.id:
            message.id = str(uuid.uuid4())

        with self._get_conn() as conn:
            # 1. 插入消息
            conn.execute("""
                INSERT INTO messages
                (id, conversation_id, role, content, timestamp, session_id,
                 intent, response_time_ms, tokens_used, trace)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                message.id, message.conversation_id, message.role,
                message.content,
                message.timestamp.isoformat() if message.timestamp else datetime.now().isoformat(),
                message.session_id,
                message.intent, message.response_time_ms, message.tokens_used,
                json.dumps(message.trace, ensure_ascii=False)
            ))

            # 2. 更新会话统计
            conn.execute("""
                UPDATE conversations
                SET message_count = message_count + 1,
                    updated_at = ?,
                    last_message = CASE
                        WHEN ? = 'user' THEN substr(?, 1, 100)
                        ELSE last_message
                    END
                WHERE id = ?
            """, (
                datetime.now().isoformat(),
                message.role,
                message.content,
                message.conversation_id
            ))

        return message.id

    def get_conversation_messages(self, conversation_id: str,
                                limit: int = 100) -> List[Message]:
        """
        获取会话的所有消息

        Args:
            conversation_id: 会话ID
            limit: 返回数量限制

        Returns:
            消息列表（按时间正序）
        """
        with self._get_conn() as conn:
            rows = conn.execute("""
                SELECT * FROM messages
                WHERE conversation_id = ?
                ORDER BY timestamp ASC
                LIMIT ?
            """, (conversation_id, limit)).fetchall()

        return [self._row_to_message(r) for r in rows]

    def get_recent_messages(self, conversation_id: str,
                          limit: int = 20) -> List[Message]:
        """
        获取会话的最近消息（用于LLM上下文）

        Args:
            conversation_id: 会话ID
            limit: 返回数量限制

        Returns:
            消息列表（按时间倒序，最近的消息在前）
        """
        with self._get_conn() as conn:
            rows = conn.execute("""
                SELECT * FROM messages
                WHERE conversation_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (conversation_id, limit)).fetchall()

        # 返回按时间正序排列（从旧到新）
        return [self._row_to_message(r) for r in reversed(rows)]

    def delete_conversation_messages(self, conversation_id: str):
        """删除会话的所有消息"""
        with self._get_conn() as conn:
            conn.execute("DELETE FROM messages WHERE conversation_id = ?",
                       (conversation_id,))

    def get_message_count(self, conversation_id: str) -> int:
        """获取会话的消息数量"""
        with self._get_conn() as conn:
            row = conn.execute("""
                SELECT COUNT(*) as count FROM messages
                WHERE conversation_id = ?
            """, (conversation_id,)).fetchone()

        return row["count"] if row else 0

    # ============ 统计操作 ============

    def get_user_stats(self, user_name: str = "") -> dict:
        """获取用户会话统计"""
        with self._get_conn() as conn:
            if user_name:
                # 特定用户
                conv_count = conn.execute(
                    "SELECT COUNT(*) FROM conversations WHERE user_name = ?",
                    (user_name,)
                ).fetchone()[0]
                msg_count = conn.execute("""
                    SELECT COUNT(*) FROM messages m
                    JOIN conversations c ON m.conversation_id = c.id
                    WHERE c.user_name = ?
                """, (user_name,)).fetchone()[0]
            else:
                # 所有用户
                conv_count = conn.execute(
                    "SELECT COUNT(*) FROM conversations"
                ).fetchone()[0]
                msg_count = conn.execute(
                    "SELECT COUNT(*) FROM messages"
                ).fetchone()[0]

        return {
            "total_conversations": conv_count,
            "total_messages": msg_count,
        }

    # ============ 辅助方法 ============

    def _row_to_conversation(self, row) -> Conversation:
        """Row转Conversation"""
        return Conversation(
            id=row["id"],
            title=row["title"],
            user_name=row["user_name"] or "",
            session_id=row["session_id"] or "",
            metadata=json.loads(row["metadata"] or "{}"),
            created_at=_parse_datetime(row["created_at"]),
            updated_at=_parse_datetime(row["updated_at"]),
            message_count=row["message_count"],
            last_message=row["last_message"],
        )

    def _row_to_message(self, row) -> Message:
        """Row转Message"""
        return Message(
            id=row["id"],
            conversation_id=row["conversation_id"],
            role=row["role"],
            content=row["content"],
            timestamp=_parse_datetime(row["timestamp"]),
            session_id=row["session_id"] or "",
            intent=row["intent"] or "",
            response_time_ms=row["response_time_ms"],
            tokens_used=row["tokens_used"],
            trace=json.loads(row["trace"] or "[]"),
        )

    # ============ 高级功能 ============

    def auto_title_conversation(self, conversation_id: str) -> str:
        """
        自动生成会话标题（基于前几条消息）

        Args:
            conversation_id: 会话ID

        Returns:
            生成的标题
        """
        # 获取前5条消息
        messages = self.get_conversation_messages(conversation_id, limit=5)

        if not messages:
            return "空对话"

        # 提取用户消息内容
        user_messages = [msg.content for msg in messages if msg.role == "user"]
        if not user_messages:
            return "对话"

        # 使用第一条用户消息作为标题基础
        first_message = user_messages[0]
        if len(first_message) > 30:
            return first_message[:27] + "..."
        return first_message

    def import_conversation_history(self, session_id: str, conversation_history: List[dict],
                                  user_name: str = "", title: str = None) -> str:
        """
        导入对话历史到持久化存储

        Args:
            session_id: 会话标识
            conversation_history: 对话历史列表 [{"role": "...", "content": "..."}, ...]
            user_name: 用户名
            title: 自定义标题（为空则自动生成）

        Returns:
            创建的会话ID
        """
        if not conversation_history:
            return ""

        # 创建会话
        if not title:
            # 基于第一条用户消息生成标题
            user_msgs = [msg["content"] for msg in conversation_history if msg.get("role") == "user"]
            title = self._generate_title_from_content(user_msgs[0]) if user_msgs else "导入的对话"

        conversation_id = self.create_conversation(
            title=title,
            user_name=user_name,
            session_id=session_id,
            metadata={"imported": True}
        )

        # 导入消息
        for msg_data in conversation_history:
            message = Message(
                id=str(uuid.uuid4()),
                conversation_id=conversation_id,
                role=msg_data.get("role", ""),
                content=msg_data.get("content", ""),
                session_id=session_id,
                timestamp=datetime.now()
            )
            self.add_message(message)

        return conversation_id

    @staticmethod
    def _generate_title_from_content(content: str) -> str:
        """从内容生成标题"""
        content = content.strip()
        if len(content) <= 30:
            return content

        # 截取并添加省略号
        return content[:27].rstrip() + "..."

    def cleanup_old_conversations(self, days: int = 30):
        """
        清理旧会话（谨慎操作）

        Args:
            days: 保留最近N天的会话
        """
        with self._get_conn() as conn:
            # 删除旧会话（级联删除消息）
            conn.execute("""
                DELETE FROM conversations
                WHERE updated_at < datetime('now', ?)
            """, (f"-{days} days",))
