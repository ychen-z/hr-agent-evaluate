from typing import Optional
from pydantic import BaseModel

class Education(BaseModel):
    degree: str
    major: str
    school: str
    year: int

class Experience(BaseModel):
    company: str
    position: str
    duration: str
    description: str

class Resume(BaseModel):
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    education: list[Education]
    experience: list[Experience]
    skills: list[str]
    soft_skills: list[str]

class JDRequirements(BaseModel):
    required_skills: list[str]
    experience_years: int
    education_level: str
    soft_skills: list[str]

class DimensionScore(BaseModel):
    score: int
    matched: list[str] = []
    missing: list[str] = []
    detail: Optional[str] = None
    
    # AI 增强字段
    baseline_score: Optional[int] = None  # 算法基准分
    adjustment_reasoning: Optional[str] = None  # AI 调整推理
    highlights: Optional[list[str]] = None  # 亮点
    concerns: Optional[list[str]] = None  # 关注点

class MatchReport(BaseModel):
    overall_score: int
    dimensions: dict
    recommendation: str
    reasons: list[str]
    
    # AI 增强字段
    overall_assessment: Optional[dict] = None  # AI 整体评估
    top_strengths: Optional[list[str]] = None  # 核心优势
    key_concerns: Optional[list[str]] = None  # 关键关注点

class MatchRequest(BaseModel):
    resume: Resume
    job_description: str

class AgentResult(BaseModel):
    session_id: str
    report: MatchReport
    html: str
    reasoning: str
