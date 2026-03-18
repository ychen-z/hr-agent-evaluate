from app.types.models import Resume, JDRequirements, DimensionScore
from app.utils.scorer import Scorer
import re

class Matcher:
    def __init__(self):
        self.scorer = Scorer()
    
    def match(self, resume: Resume, requirements: JDRequirements) -> dict[str, DimensionScore]:
        resume_years = self._calculate_years(resume.experience)
        
        results = {
            "hard_skills": self.scorer.score_hard_skills(
                resume.skills,
                requirements.required_skills
            ),
            "experience": self.scorer.score_experience(
                resume_years,
                requirements.experience_years
            ),
            "education": self.scorer.score_education(
                self._get_highest_degree(resume.education),
                requirements.education_level
            ),
            "soft_skills": self.scorer.score_soft_skills(
                resume.soft_skills,
                requirements.soft_skills
            )
        }
        
        return results
    
    def _calculate_years(self, experiences: list) -> int:
        total = 0
        for exp in experiences:
            match = re.search(r'(\d+)年', exp.duration)
            if match:
                total += int(match.group(1))
        return total
    
    def _get_highest_degree(self, education: list) -> str:
        degrees = [e.degree for e in education]
        priority = ["博士", "硕士", "本科", "大专"]
        for d in priority:
            if d in degrees:
                return d
        return "本科"
