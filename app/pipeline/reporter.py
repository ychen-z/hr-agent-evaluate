from app.types.models import DimensionScore
from app.utils.scorer import Scorer

THRESHOLD = 70

class Reporter:
    def __init__(self):
        self.scorer = Scorer()
    
    def generate(self, dimension_scores: dict) -> dict:
        overall = self.scorer.calculate_overall(dimension_scores)
        
        recommendation = "推荐" if overall >= THRESHOLD else "不推荐"
        
        # 检查是否包含 AI 字段
        has_ai_fields = self._has_ai_fields(dimension_scores)
        
        # 生成理由
        if has_ai_fields:
            reasons = self._generate_ai_reasons(dimension_scores)
        else:
            reasons = self._generate_algorithm_reasons(dimension_scores)
        
        if not reasons:
            reasons.append("综合评估结果")
        
        result = {
            "overall_score": overall,
            "dimensions": {k: v.model_dump() for k, v in dimension_scores.items()},
            "recommendation": recommendation,
            "reasons": reasons
        }
        
        # 如果有 AI 增强字段,收集整体信息
        if has_ai_fields:
            top_strengths = []
            key_concerns = []
            
            for dim_score in dimension_scores.values():
                if dim_score.highlights:
                    top_strengths.extend(dim_score.highlights)
                if dim_score.concerns:
                    key_concerns.extend(dim_score.concerns)
            
            # 去重并限制数量
            if top_strengths:
                result["top_strengths"] = list(dict.fromkeys(top_strengths))[:5]
            if key_concerns:
                result["key_concerns"] = list(dict.fromkeys(key_concerns))[:3]
        
        return result
    
    def _has_ai_fields(self, dimension_scores: dict) -> bool:
        """检查是否包含 AI 增强字段"""
        for dim_score in dimension_scores.values():
            if dim_score.adjustment_reasoning or dim_score.highlights or dim_score.concerns:
                return True
        return False
    
    def _generate_ai_reasons(self, dimension_scores: dict) -> list[str]:
        """从 AI highlights 生成推荐理由"""
        reasons = []
        
        # 优先使用 highlights
        for dim_name, dim_score in dimension_scores.items():
            if dim_score.highlights:
                reasons.extend(dim_score.highlights)
        
        # 如果没有 highlights,使用传统逻辑
        if not reasons:
            reasons = self._generate_algorithm_reasons(dimension_scores)
        
        return reasons
    
    def _generate_algorithm_reasons(self, dimension_scores: dict) -> list[str]:
        """传统算法生成推荐理由"""
        reasons = []
        if dimension_scores.get("hard_skills", DimensionScore(score=0)).score >= 80:
            reasons.append("技术栈匹配度高")
        if dimension_scores.get("experience", DimensionScore(score=0)).score >= 100:
            reasons.append("工作经验符合要求")
        if dimension_scores.get("education", DimensionScore(score=0)).score >= 100:
            reasons.append("教育背景符合要求")
        if dimension_scores.get("soft_skills", DimensionScore(score=0)).score >= 80:
            reasons.append("软技能匹配")
        return reasons
