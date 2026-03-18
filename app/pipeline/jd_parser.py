import re
import json
from anthropic import Anthropic
from app.types.models import JDRequirements
import os

class JDParser:
    def __init__(self):
        api_key = os.getenv("ANTHROPIC_API_KEY")
        self.client = Anthropic(api_key=api_key) if api_key else None

    def parse(self, jd_text: str) -> JDRequirements:
        prompt = f"""从以下职位描述中提取结构化需求，返回JSON格式：
职位描述: {jd_text}

请提取：
1. required_skills: 技术栈要求（列出具体技能）
2. experience_years: 工作年限要求（数字）
3. education_level: 学历要求（大专/本科/硕士/博士）
4. soft_skills: 软技能要求

只返回JSON，不要其他内容。格式：
{{"required_skills": [], "experience_years": 0, "education_level": "", "soft_skills": []}}"""

        if self.client:
            response = self.client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}]
            )
            result = json.loads(response.content[0].text)
            return JDRequirements(**result)
        else:
            return self._fallback_parse(jd_text)

    def _fallback_parse(self, jd_text: str) -> JDRequirements:
        skills = []
        years_match = re.search(r'(\d+)年', jd_text)
        years = int(years_match.group(1)) if years_match else 0
        
        edu_match = re.search(r'(博士|硕士|本科|大专)', jd_text)
        education = edu_match.group(1) if edu_match else "本科"
        
        soft_skills = []
        if "沟通" in jd_text:
            soft_skills.append("沟通能力")
        if "团队" in jd_text:
            soft_skills.append("团队协作")
            
        if "Python" in jd_text:
            skills.append("Python")
        if "Golang" in jd_text:
            skills.append("Golang")
            
        return JDRequirements(
            required_skills=skills,
            experience_years=years,
            education_level=education,
            soft_skills=soft_skills
        )
