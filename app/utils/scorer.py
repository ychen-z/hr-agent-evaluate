from app.types.models import JDRequirements, Resume, DimensionScore

class Scorer:
    EDUCATION_LEVELS = {
        "大专": 2,
        "本科": 3,
        "硕士": 4,
        "博士": 5
    }
    
    WEIGHTS = {
        "hard_skills": 0.4,
        "experience": 0.3,
        "education": 0.15,
        "soft_skills": 0.15
    }
    
    def score_hard_skills(self, resume_skills: list[str], required_skills: list[str]) -> DimensionScore:
        if not required_skills:
            return DimensionScore(score=100, matched=[], missing=[])
        
        resume_lower = [s.lower() for s in resume_skills]
        matched = [s for s in required_skills if s.lower() in resume_lower]
        missing = [s for s in required_skills if s.lower() not in resume_lower]
        
        score = int(len(matched) / len(required_skills) * 100)
        score = min(score, 100)
        
        return DimensionScore(score=score, matched=matched, missing=missing)
    
    def score_experience(self, resume_years: int, required_years: int) -> DimensionScore:
        if required_years == 0:
            return DimensionScore(score=100, detail="无年限要求")
        
        score = int(resume_years / required_years * 100)
        score = min(score, 100)
        
        return DimensionScore(
            score=score,
            detail=f"{resume_years}年 vs 要求{required_years}年"
        )
    
    def score_education(self, resume_degree: str, required_degree: str) -> DimensionScore:
        actual = self.EDUCATION_LEVELS.get(resume_degree, 0)
        required = self.EDUCATION_LEVELS.get(required_degree, 0)
        
        if actual >= required:
            score = 100
        else:
            score = int(actual / required * 100)
        
        return DimensionScore(
            score=score,
            detail=f"{resume_degree} vs 要求{required_degree}"
        )
    
    def score_soft_skills(self, resume_skills: list[str], required_skills: list[str]) -> DimensionScore:
        if not required_skills:
            return DimensionScore(score=100, matched=[], missing=[])
        
        matched = [s for s in required_skills if s in resume_skills]
        missing = [s for s in required_skills if s not in resume_skills]
        
        score = int(len(matched) / len(required_skills) * 100)
        score = min(score, 100)
        
        return DimensionScore(score=score, matched=matched, missing=missing)
    
    def calculate_overall(self, dimension_scores: dict) -> int:
        total = 0
        for dim, weight in self.WEIGHTS.items():
            if dim in dimension_scores:
                total += dimension_scores[dim].score * weight
        return int(total)
