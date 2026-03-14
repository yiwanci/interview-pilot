"""
SM-2 遗忘曲线算法
基于 SuperMemo 2 算法，Anki 同款
"""
from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass
class SM2Result:
    """SM-2 计算结果"""
    ease_factor: float       # 新的难易因子
    interval_days: int       # 下次复习间隔（天）
    repetitions: int         # 连续正确次数
    mastery_level: float     # 掌握程度 0~1
    next_review_at: datetime # 下次复习时间


class SM2Engine:
    """
    SM-2 遗忘曲线引擎
    
    评分标准 (0-5):
        5 - 完美，毫不犹豫
        4 - 正确，稍有犹豫  
        3 - 正确但很吃力
        2 - 错误，看答案后想起来了
        1 - 错误，看答案有点印象
        0 - 完全不会
    
    使用示例:
        engine = SM2Engine()
        result = engine.calculate(score=4, current_ease=2.5, current_interval=6, current_reps=2)
        print(result.next_review_at)
    """
    
    # 默认参数
    DEFAULT_EASE = 2.5
    MIN_EASE = 1.3
    FIRST_INTERVAL = 1
    SECOND_INTERVAL = 6
    
    @classmethod
    def calculate(
        cls,
        score: int,
        current_ease: float = DEFAULT_EASE,
        current_interval: int = 0,
        current_reps: int = 0,
    ) -> SM2Result:
        """
        计算下次复习时间
        
        Args:
            score: 本次评分 0-5
            current_ease: 当前难易因子
            current_interval: 当前间隔天数
            current_reps: 当前连续正确次数
        
        Returns:
            SM2Result: 计算结果
        """
        score = max(0, min(5, score))  # 限制在 0-5
        
        # 评分 >= 3 视为"记住了"
        if score >= 3:
            if current_reps == 0:
                interval = cls.FIRST_INTERVAL
            elif current_reps == 1:
                interval = cls.SECOND_INTERVAL
            else:
                interval = round(current_interval * current_ease)
            repetitions = current_reps + 1
        else:
            # 没记住，重置
            interval = cls.FIRST_INTERVAL
            repetitions = 0
        
        # 更新难易因子（SM-2 核心公式）
        new_ease = current_ease + (0.1 - (5 - score) * (0.08 + (5 - score) * 0.02))
        new_ease = max(cls.MIN_EASE, new_ease)
        
        # 计算掌握程度
        mastery = cls._calculate_mastery(repetitions, score)
        
        # 下次复习时间
        next_review = datetime.now() + timedelta(days=interval)
        
        return SM2Result(
            ease_factor=round(new_ease, 2),
            interval_days=interval,
            repetitions=repetitions,
            mastery_level=round(mastery, 2),
            next_review_at=next_review,
        )
    
    @staticmethod
    def _calculate_mastery(repetitions: int, score: int) -> float:
        """
        计算掌握程度
        综合考虑：连续正确次数 + 本次评分
        """
        # 基础分：连续正确次数贡献
        base = min(0.7, repetitions * 0.12)
        # 本次评分贡献
        score_bonus = (score / 5.0) * 0.3
        return min(1.0, base + score_bonus)
    
    @classmethod
    def get_score_description(cls, score: int) -> str:
        """获取评分描述"""
        descriptions = {
            5: "完美掌握，毫不犹豫",
            4: "基本掌握，稍有犹豫",
            3: "勉强记得，比较吃力",
            2: "回答错误，看答案后想起来",
            1: "回答错误，看答案有印象",
            0: "完全不会，没有印象",
        }
        return descriptions.get(score, "未知")
    
    @classmethod
    def estimate_review_schedule(cls, target_mastery: float = 0.9) -> list[dict]:
        """
        估算达到目标掌握度需要的复习计划
        假设每次都得 4 分
        """
        schedule = []
        ease = cls.DEFAULT_EASE
        interval = 0
        reps = 0
        total_days = 0
        
        while True:
            result = cls.calculate(
                score=4,
                current_ease=ease,
                current_interval=interval,
                current_reps=reps,
            )
            
            total_days += result.interval_days
            schedule.append({
                "review_number": reps + 1,
                "days_from_start": total_days,
                "interval": result.interval_days,
                "mastery": result.mastery_level,
            })
            
            if result.mastery_level >= target_mastery:
                break
            
            ease = result.ease_factor
            interval = result.interval_days
            reps = result.repetitions
            
            if len(schedule) > 20:  # 防止无限循环
                break
        
        return schedule
