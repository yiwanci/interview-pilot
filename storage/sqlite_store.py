"""
SQLite 数据库操作
"""
import sqlite3
import json
import uuid
from datetime import datetime, date
from typing import Optional
from contextlib import contextmanager

from config import SQLITE_DB_PATH
from .models import KnowledgePoint, StudyLog, UserProfile


class SQLiteStore:
    def __init__(self, db_path=None):
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
        """初始化表结构"""
        with self._get_conn() as conn:
            conn.executescript("""
                -- 知识点表
                CREATE TABLE IF NOT EXISTS knowledge_points (
                    id              TEXT PRIMARY KEY,
                    name            TEXT NOT NULL,
                    category        TEXT NOT NULL,
                    domain          TEXT NOT NULL,
                    tags            TEXT,
                    difficulty      INTEGER DEFAULT 3,
                    ease_factor     REAL DEFAULT 2.5,
                    interval_days   INTEGER DEFAULT 0,
                    repetitions     INTEGER DEFAULT 0,
                    mastery_level   REAL DEFAULT 0.0,
                    last_review_at  TIMESTAMP,
                    next_review_at  TIMESTAMP,
                    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    mem0_memory_ids TEXT,
                    related_qa_ids  TEXT
                );
                
                -- 学习日志表
                CREATE TABLE IF NOT EXISTS study_logs (
                    id              TEXT PRIMARY KEY,
                    date            DATE NOT NULL,
                    knowledge_id    TEXT,
                    activity_type   TEXT NOT NULL,
                    duration_min    INTEGER DEFAULT 0,
                    score           INTEGER,
                    llm_score       INTEGER,
                    user_score      INTEGER,
                    summary         TEXT,
                    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (knowledge_id) REFERENCES knowledge_points(id)
                );
                
                -- 用户画像表
                CREATE TABLE IF NOT EXISTS user_profile (
                    key             TEXT PRIMARY KEY,
                    value           TEXT NOT NULL,
                    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                -- 创建索引
                CREATE INDEX IF NOT EXISTS idx_kp_domain ON knowledge_points(domain);
                CREATE INDEX IF NOT EXISTS idx_kp_next_review ON knowledge_points(next_review_at);
                CREATE INDEX IF NOT EXISTS idx_kp_mastery ON knowledge_points(mastery_level);
                CREATE INDEX IF NOT EXISTS idx_log_date ON study_logs(date);
            """)
    
    # ============ 知识点操作 ============
    
    def create_knowledge_point(self, kp: KnowledgePoint) -> str:
        """创建知识点"""
        if not kp.id:
            kp.id = str(uuid.uuid4())
        
        with self._get_conn() as conn:
            conn.execute("""
                INSERT INTO knowledge_points 
                (id, name, category, domain, tags, difficulty, ease_factor, 
                 interval_days, repetitions, mastery_level, next_review_at, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                kp.id, kp.name, kp.category, kp.domain,
                json.dumps(kp.tags, ensure_ascii=False),
                kp.difficulty, kp.ease_factor, kp.interval_days,
                kp.repetitions, kp.mastery_level, kp.next_review_at, kp.created_at
            ))
        return kp.id
    
    def get_knowledge_point(self, kp_id: str) -> Optional[KnowledgePoint]:
        """获取单个知识点"""
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM knowledge_points WHERE id = ?", (kp_id,)
            ).fetchone()
        
        if row:
            return self._row_to_knowledge_point(row)
        return None
    
    def update_knowledge_point(self, kp: KnowledgePoint):
        """更新知识点"""
        with self._get_conn() as conn:
            conn.execute("""
                UPDATE knowledge_points SET
                    ease_factor = ?, interval_days = ?, repetitions = ?,
                    mastery_level = ?, last_review_at = ?, next_review_at = ?,
                    mem0_memory_ids = ?, related_qa_ids = ?
                WHERE id = ?
            """, (
                kp.ease_factor, kp.interval_days, kp.repetitions,
                kp.mastery_level, kp.last_review_at, kp.next_review_at,
                json.dumps(kp.mem0_memory_ids), json.dumps(kp.related_qa_ids),
                kp.id
            ))
    
    def get_due_reviews(self, limit: int = 20) -> list[KnowledgePoint]:
        """获取到期需要复习的知识点"""
        today = date.today().isoformat()
        with self._get_conn() as conn:
            rows = conn.execute("""
                SELECT * FROM knowledge_points 
                WHERE next_review_at <= ? OR next_review_at IS NULL
                ORDER BY mastery_level ASC, next_review_at ASC
                LIMIT ?
            """, (today, limit)).fetchall()
        
        return [self._row_to_knowledge_point(r) for r in rows]
    
    def get_weak_points(self, domain: str = None, threshold: float = 0.6, limit: int = 10) -> list[KnowledgePoint]:
        """获取薄弱知识点"""
        with self._get_conn() as conn:
            if domain:
                rows = conn.execute("""
                    SELECT * FROM knowledge_points 
                    WHERE mastery_level < ? AND domain = ?
                    ORDER BY mastery_level ASC
                    LIMIT ?
                """, (threshold, domain, limit)).fetchall()
            else:
                rows = conn.execute("""
                    SELECT * FROM knowledge_points 
                    WHERE mastery_level < ?
                    ORDER BY mastery_level ASC
                    LIMIT ?
                """, (threshold, limit)).fetchall()
        
        return [self._row_to_knowledge_point(r) for r in rows]
    
    def search_knowledge_points(self, keyword: str, domain: str = None) -> list[KnowledgePoint]:
        """搜索知识点"""
        with self._get_conn() as conn:
            if domain:
                rows = conn.execute("""
                    SELECT * FROM knowledge_points 
                    WHERE (name LIKE ? OR tags LIKE ?) AND domain = ?
                """, (f"%{keyword}%", f"%{keyword}%", domain)).fetchall()
            else:
                rows = conn.execute("""
                    SELECT * FROM knowledge_points 
                    WHERE name LIKE ? OR tags LIKE ?
                """, (f"%{keyword}%", f"%{keyword}%")).fetchall()
        
        return [self._row_to_knowledge_point(r) for r in rows]
    
    def get_all_knowledge_points(self, domain: str = None) -> list[KnowledgePoint]:
        """获取所有知识点"""
        with self._get_conn() as conn:
            if domain:
                rows = conn.execute(
                    "SELECT * FROM knowledge_points WHERE domain = ?", (domain,)
                ).fetchall()
            else:
                rows = conn.execute("SELECT * FROM knowledge_points").fetchall()
        
        return [self._row_to_knowledge_point(r) for r in rows]
    
    def _row_to_knowledge_point(self, row) -> KnowledgePoint:
        """Row转KnowledgePoint"""
        return KnowledgePoint(
            id=row["id"],
            name=row["name"],
            category=row["category"],
            domain=row["domain"],
            tags=json.loads(row["tags"] or "[]"),
            difficulty=row["difficulty"],
            ease_factor=row["ease_factor"],
            interval_days=row["interval_days"],
            repetitions=row["repetitions"],
            mastery_level=row["mastery_level"],
            last_review_at=row["last_review_at"],
            next_review_at=row["next_review_at"],
            created_at=row["created_at"],
            mem0_memory_ids=json.loads(row["mem0_memory_ids"] or "[]"),
            related_qa_ids=json.loads(row["related_qa_ids"] or "[]"),
        )
    
    # ============ 学习日志操作 ============
    
    def add_study_log(self, log: StudyLog) -> str:
        """添加学习日志"""
        if not log.id:
            log.id = str(uuid.uuid4())
        
        with self._get_conn() as conn:
            conn.execute("""
                INSERT INTO study_logs 
                (id, date, knowledge_id, activity_type, duration_min, 
                 score, llm_score, user_score, summary)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                log.id, log.date, log.knowledge_id, log.activity_type,
                log.duration_min, log.score, log.llm_score, log.user_score, log.summary
            ))
        return log.id
    
    def get_study_logs(self, start_date: date = None, end_date: date = None) -> list[StudyLog]:
        """获取学习日志"""
        with self._get_conn() as conn:
            if start_date and end_date:
                rows = conn.execute("""
                    SELECT * FROM study_logs 
                    WHERE date BETWEEN ? AND ?
                    ORDER BY date DESC
                """, (start_date.isoformat(), end_date.isoformat())).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM study_logs ORDER BY date DESC LIMIT 100"
                ).fetchall()
        
        return [self._row_to_study_log(r) for r in rows]
    
    def _row_to_study_log(self, row) -> StudyLog:
        """Row转StudyLog"""
        return StudyLog(
            id=row["id"],
            date=row["date"],
            knowledge_id=row["knowledge_id"],
            activity_type=row["activity_type"],
            duration_min=row["duration_min"],
            score=row["score"],
            llm_score=row["llm_score"],
            user_score=row["user_score"],
            summary=row["summary"],
            created_at=row["created_at"],
        )
    
    # ============ 用户画像操作 ============
    
    def set_profile(self, key: str, value):
        """设置用户画像"""
        with self._get_conn() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO user_profile (key, value, updated_at)
                VALUES (?, ?, ?)
            """, (key, json.dumps(value, ensure_ascii=False), datetime.now()))
    
    def get_profile(self, key: str, default=None):
        """获取用户画像"""
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT value FROM user_profile WHERE key = ?", (key,)
            ).fetchone()
        
        if row:
            return json.loads(row["value"])
        return default
    
    def get_full_profile(self) -> UserProfile:
        """获取完整用户画像"""
        return UserProfile(
            target_positions=self.get_profile("target_positions", []),
            target_companies=self.get_profile("target_companies", []),
            tech_stack=self.get_profile("tech_stack", []),
            weak_areas=self.get_profile("weak_areas", []),
            study_preference=self.get_profile("study_preference", {}),
        )
    
    # ============ 统计 ============
    
    def get_stats(self) -> dict:
        """获取学习统计"""
        with self._get_conn() as conn:
            total_kp = conn.execute("SELECT COUNT(*) FROM knowledge_points").fetchone()[0]
            mastered = conn.execute(
                "SELECT COUNT(*) FROM knowledge_points WHERE mastery_level >= 0.8"
            ).fetchone()[0]
            due_review = conn.execute(
                "SELECT COUNT(*) FROM knowledge_points WHERE next_review_at <= date('now')"
            ).fetchone()[0]
            total_logs = conn.execute("SELECT COUNT(*) FROM study_logs").fetchone()[0]
        
        return {
            "total_knowledge_points": total_kp,
            "mastered_count": mastered,
            "due_review_count": due_review,
            "total_study_logs": total_logs,
        }
