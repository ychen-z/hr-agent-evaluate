from app.types.models import DimensionScore
from app.utils.scorer import Scorer

THRESHOLD = 70

class Reporter:
    def __init__(self):
        self.scorer = Scorer()
    
    def generate(self, dimension_scores: dict) -> dict:
        overall = self.scorer.calculate_overall(dimension_scores)
        
        recommendation = "推荐" if overall >= THRESHOLD else "不推荐"
        
        reasons = []
        if dimension_scores.get("hard_skills", DimensionScore(score=0)).score >= 80:
            reasons.append("技术栈匹配度高")
        if dimension_scores.get("experience", DimensionScore(score=0)).score >= 100:
            reasons.append("工作经验符合要求")
        if dimension_scores.get("education", DimensionScore(score=0)).score >= 100:
            reasons.append("教育背景符合要求")
        if dimension_scores.get("soft_skills", DimensionScore(score=0)).score >= 80:
            reasons.append("软技能匹配")
        
        if not reasons:
            reasons.append("综合评估结果")
        
        return {
            "overall_score": overall,
            "dimensions": {k: v.model_dump() for k, v in dimension_scores.items()},
            "recommendation": recommendation,
            "reasons": reasons
        }
