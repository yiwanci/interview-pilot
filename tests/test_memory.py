"""
记忆系统测试
"""
import pytest
from datetime import datetime, timedelta

from memory import SM2Engine, SM2Result, MemoryManager
from storage import SQLiteStore, KnowledgePoint


class TestSM2Engine:
    """SM-2 算法测试"""
    
    def test_first_review_score_5(self):
        """首次复习得5分"""
        result = SM2Engine.calculate(score=5)
        
        assert result.interval_days == 1
        assert result.repetitions == 1
        assert result.ease_factor >= 2.5
        assert result.mastery_level > 0
    
    def test_first_review_score_0(self):
        """首次复习得0分"""
        result = SM2Engine.calculate(score=0)
        
        assert result.interval_days == 1
        assert result.repetitions == 0
        assert result.ease_factor < 2.5
    
    def test_second_review(self):
        """第二次复习"""
        result = SM2Engine.calculate(
            score=4,
            current_ease=2.5,
            current_interval=1,
            current_reps=1
        )
        
        assert result.interval_days == 6
        assert result.repetitions == 2
    
    def test_interval_increases(self):
        """间隔递增测试"""
        ease = 2.5
        interval = 6
        reps = 2
        
        # 连续得4分，间隔应该递增
        intervals = []
        for _ in range(5):
            result = SM2Engine.calculate(
                score=4,
                current_ease=ease,
                current_interval=interval,
                current_reps=reps
            )
            intervals.append(result.interval_days)
            ease = result.ease_factor
            interval = result.interval_days
            reps = result.repetitions
        
        # 验证间隔递增
        for i in range(1, len(intervals)):
            assert intervals[i] >= intervals[i-1]
    
    def test_reset_on_fail(self):
        """失败后重置"""
        # 先学到一定程度
        result = SM2Engine.calculate(score=4, current_reps=3, current_interval=15)
        
        # 然后失败
        result = SM2Engine.calculate(
            score=1,
            current_ease=result.ease_factor,
            current_interval=result.interval_days,
            current_reps=result.repetitions
        )
        
        assert result.interval_days == 1
        assert result.repetitions == 0
    
    def test_mastery_increases(self):
        """掌握度递增"""
        ease = 2.5
        interval = 0
        reps = 0
        
        masteries = []
        for _ in range(6):
            result = SM2Engine.calculate(
                score=5,
                current_ease=ease,
                current_interval=interval,
                current_reps=reps
            )
            masteries.append(result.mastery_level)
            ease = result.ease_factor
            interval = result.interval_days
            reps = result.repetitions
        
        # 掌握度应该递增
        for i in range(1, len(masteries)):
            assert masteries[i] >= masteries[i-1]
        
        # 最终应该接近1.0
        assert masteries[-1] >= 0.8
    
    def test_score_description(self):
        """评分描述"""
        assert "完美" in SM2Engine.get_score_description(5)
        assert "不会" in SM2Engine.get_score_description(0)


class TestSQLiteStore:
    """SQLite 存储测试"""
    
    @pytest.fixture
    def db(self, tmp_path):
        """创建临时数据库"""
        db_path = tmp_path / "test.db"
        return SQLiteStore(db_path=db_path)
    
    def test_create_knowledge_point(self, db):
        """创建知识点"""
        kp = KnowledgePoint(
            id="test-1",
            name="Redis RDB",
            category="database",
            domain="java_backend",
            tags=["Redis", "持久化"],
        )
        
        kp_id = db.create_knowledge_point(kp)
        assert kp_id == "test-1"
        
        # 读取验证
        loaded = db.get_knowledge_point("test-1")
        assert loaded is not None
        assert loaded.name == "Redis RDB"
        assert "Redis" in loaded.tags
    
    def test_update_knowledge_point(self, db):
        """更新知识点"""
        kp = KnowledgePoint(
            id="test-2",
            name="JVM GC",
            category="java_basic",
            domain="java_backend",
        )
        db.create_knowledge_point(kp)
        
        # 更新
        kp.mastery_level = 0.5
        kp.repetitions = 3
        db.update_knowledge_point(kp)
        
        # 验证
        loaded = db.get_knowledge_point("test-2")
        assert loaded.mastery_level == 0.5
        assert loaded.repetitions == 3
    
    def test_get_due_reviews(self, db):
        """获取待复习知识点"""
        # 创建已到期的
        kp1 = KnowledgePoint(
            id="due-1",
            name="到期知识点",
            category="test",
            domain="test",
            next_review_at=datetime.now() - timedelta(days=1),
        )
        db.create_knowledge_point(kp1)
        
        # 创建未到期的
        kp2 = KnowledgePoint(
            id="not-due",
            name="未到期知识点",
            category="test",
            domain="test",
            next_review_at=datetime.now() + timedelta(days=7),
        )
        db.create_knowledge_point(kp2)
        
        # 获取待复习
        due = db.get_due_reviews()
        due_ids = [k.id for k in due]
        
        assert "due-1" in due_ids
        assert "not-due" not in due_ids
    
    def test_get_weak_points(self, db):
        """获取薄弱知识点"""
        # 创建薄弱的
        kp1 = KnowledgePoint(
            id="weak-1",
            name="薄弱知识点",
            category="test",
            domain="java_backend",
            mastery_level=0.2,
        )
        db.create_knowledge_point(kp1)
        
        # 创建掌握好的
        kp2 = KnowledgePoint(
            id="strong-1",
            name="掌握好的",
            category="test",
            domain="java_backend",
            mastery_level=0.9,
        )
        db.create_knowledge_point(kp2)
        
        # 获取薄弱点
        weak = db.get_weak_points(threshold=0.6)
        weak_ids = [k.id for k in weak]
        
        assert "weak-1" in weak_ids
        assert "strong-1" not in weak_ids
    
    def test_search_knowledge_points(self, db):
        """搜索知识点"""
        kp = KnowledgePoint(
            id="search-1",
            name="HashMap底层原理",
            category="java_basic",
            domain="java_backend",
            tags=["集合框架", "数据结构"],
        )
        db.create_knowledge_point(kp)
        
        # 按名称搜索
        results = db.search_knowledge_points("HashMap")
        assert len(results) > 0
        assert results[0].id == "search-1"
        
        # 按标签搜索
        results = db.search_knowledge_points("集合")
        assert len(results) > 0
    
    def test_user_profile(self, db):
        """用户画像"""
        db.set_profile("target_positions", ["Java后端", "AI Agent"])
        db.set_profile("target_companies", ["字节", "阿里"])
        
        positions = db.get_profile("target_positions")
        assert "Java后端" in positions
        
        profile = db.get_full_profile()
        assert "字节" in profile.target_companies
    
    def test_stats(self, db):
        """统计信息"""
        # 创建一些数据
        for i in range(5):
            kp = KnowledgePoint(
                id=f"stat-{i}",
                name=f"知识点{i}",
                category="test",
                domain="test",
                mastery_level=0.9 if i < 2 else 0.3,
            )
            db.create_knowledge_point(kp)
        
        stats = db.get_stats()
        assert stats["total_knowledge_points"] == 5
        assert stats["mastered_count"] == 2


class TestMemoryManager:
    """记忆管理器测试"""
    
    @pytest.fixture
    def mm(self, tmp_path, mocker):
        """创建 MemoryManager（mock Mem0）"""
        # Mock Mem0Client
        mocker.patch('memory.memory_manager.Mem0Client')
        
        # 使用临时数据库
        from config import settings
        original_path = settings.SQLITE_DB_PATH
        settings.SQLITE_DB_PATH = tmp_path / "test.db"
        
        mm = MemoryManager()
        
        yield mm
        
        settings.SQLITE_DB_PATH = original_path
    
    def test_learn_new_topic(self, mm):
        """学习新知识点"""
        kp_id = mm.learn_new_topic(
            name="Redis分布式锁",
            category="database",
            domain="java_backend",
            tags=["Redis", "分布式"],
            initial_feedback="刚开始学，概念还不清楚"
        )
        
        assert kp_id is not None
        
        # 验证知识点已创建
        kp = mm.get_knowledge_point(kp_id)
        assert kp is not None
        assert kp.name == "Redis分布式锁"
        assert kp.mastery_level == 0.0
    
    def test_review_topic(self, mm):
        """复习知识点"""
        # 先创建
        kp_id = mm.learn_new_topic(
            name="TCP三次握手",
            category="network",
            domain="cs_basic",
        )
        
        # 复习
        result = mm.review_topic(kp_id, score=4)
        
        assert result.interval_days >= 1
        assert result.mastery_level > 0
        
        # 验证更新
        kp = mm.get_knowledge_point(kp_id)
        assert kp.repetitions == 1
        assert kp.mastery_level > 0
    
    def test_get_today_plan(self, mm):
        """获取今日计划"""
        # 创建一些知识点
        mm.learn_new_topic("知识点1", "test", "test")
        mm.learn_new_topic("知识点2", "test", "test")
        
        plan = mm.get_today_plan()
        
        assert "due_reviews" in plan
        assert "weak_points" in plan
        assert "summary" in plan
    
    def test_get_context_for_agent(self, mm):
        """获取 Agent 上下文"""
        mm.learn_new_topic("Redis", "database", "java_backend")
        mm.set_user_profile(target_positions=["Java后端"])
        
        context = mm.get_context_for_agent("Redis")
        
        assert "user_profile" in context
        assert "related_knowledge" in context


def run_tests():
    """运行测试"""
    pytest.main([__file__, "-v"])


if __name__ == "__main__":
    run_tests()
