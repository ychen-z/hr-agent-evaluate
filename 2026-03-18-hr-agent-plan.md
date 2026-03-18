# HR 简历-JD 匹配评估 Agent 实现计划

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建一个基于 NLP 的简历与职位描述匹配度评估 API

**Architecture:** 三阶段流水线架构 - JD解析 → 多维度匹配 → 报告生成。使用 FastAPI + Claude API

**Tech Stack:** Python 3.10+, FastAPI, Anthropic Claude API

---

## 项目结构

```
hr-resume-match/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI 应用入口
│   ├── api/
│   │   └── __init__.py
│   │   └── routes.py        # API 路由定义
│   ├── pipeline/
│   │   ├── __init__.py
│   │   ├── jd_parser.py    # JD 解析模块
│   │   ├── matcher.py      # 匹配计算模块
│   │   └── reporter.py     # 报告生成模块
│   ├── types/
│   │   ├── __init__.py
│   │   └── models.py       # 数据模型定义
│   └── utils/
│       ├── __init__.py
│       └── scorer.py       # 评分工具
├── tests/
│   ├── __init__.py
│   ├── test_jd_parser.py
│   ├── test_matcher.py
│   ├── test_reporter.py
│   └── test_api.py
├── requirements.txt
└── .env.example
```

---

## Chunk 1: 项目初始化与基础配置

**Files:**
- Create: `hr-resume-match/requirements.txt`
- Create: `hr-resume-match/.env.example`
- Create: `hr-resume-match/app/__init__.py`
- Create: `hr-resume-match/app/types/__init__.py`
- Create: `hr-resume-match/app/types/models.py`

- [ ] **Step 1: 创建 requirements.txt**

```txt
fastapi>=0.104.0
uvicorn>=0.24.0
pydantic>=2.5.0
anthropic>=0.18.0
python-dotenv>=1.0.0
pytest>=7.4.0
pytest-asyncio>=0.21.0
httpx>=0.25.0
```

- [ ] **Step 2: 创建 .env.example**

```env
ANTHROPIC_API_KEY=your_api_key_here
API_KEY=your_api_key_here
```

- [ ] **Step 3: 创建数据模型**

```python
# app/types/models.py
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

class MatchReport(BaseModel):
    overall_score: int
    dimensions: dict
    recommendation: str
    reasons: list[str]

class MatchRequest(BaseModel):
    resume: Resume
    job_description: str
```

- [ ] **Step 4: 运行测试验证模型**

```bash
cd hr-resume-match && python -c "from app.types.models import Resume, MatchRequest; print('Models OK')"
```

- [ ] **Step 5: Commit**

```bash
cd hr-resume-match && git init && git add -A && git commit -m "feat: 项目初始化，添加数据模型定义"
```

---

## Chunk 2: JD Parser 模块

**Files:**
- Create: `hr-resume-match/app/pipeline/jd_parser.py`
- Test: `hr-resume-match/tests/test_jd_parser.py`

- [ ] **Step 1: 编写 JD Parser 测试**

```python
# tests/test_jd_parser.py
import pytest
from app.pipeline.jd_parser import JDParser
from app.types.models import JDRequirements

@pytest.fixture
def parser():
    return JDParser()

def test_parse_jd_with_all_requirements(parser):
    jd = "招聘高级后端工程师，要求熟练掌握Python或Golang，有3年以上后端开发经验，本科以上学历，具备良好的沟通能力和团队协作精神。"
    result = parser.parse(jd)
    
    assert isinstance(result, JDRequirements)
    assert "Python" in result.required_skills or "Golang" in result.required_skills
    assert result.experience_years >= 3
    assert result.education_level in ["本科", "硕士", "博士"]

def test_parse_jd_minimal(parser):
    jd = "招聘工程师"
    result = parser.parse(jd)
    
    assert isinstance(result, JDRequirements)
```

- [ ] **Step 2: 运行测试验证失败**

```bash
cd hr-resume-match && pytest tests/test_jd_parser.py -v
Expected: FAIL (JDParser not defined)

- [ ] **Step 3: 实现 JD Parser**

```python
# app/pipeline/jd_parser.py
import re
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
            import json
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
```

- [ ] **Step 4: 运行测试验证通过**

```bash
cd hr-resume-match && pytest tests/test_jd_parser.py -v
Expected: PASS
```

- [ ] **Step 5: Commit**

```bash
cd hr-resume-match && git add -A && git commit -m "feat: 添加 JD Parser 模块"
```

---

## Chunk 3: Matcher 模块

**Files:**
- Create: `hr-resume-match/app/pipeline/matcher.py`
- Create: `hr-resume-match/app/utils/scorer.py`
- Test: `hr-resume-match/tests/test_matcher.py`

- [ ] **Step 1: 创建评分工具**

```python
# app/utils/scorer.py
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
```

- [ ] **Step 2: 创建 Matcher 模块**

```python
# app/pipeline/matcher.py
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
```

- [ ] **Step 3: 编写 Matcher 测试**

```python
# tests/test_matcher.py
import pytest
from app.pipeline.matcher import Matcher
from app.types.models import Resume, Education, Experience, JDRequirements

@pytest.fixture
def matcher():
    return Matcher()

def test_match_full(matcher):
    resume = Resume(
        name="张三",
        education=[Education(degree="本科", major="计算机", school="清华", year=2018)],
        experience=[Experience(company="字节", position="工程师", duration="3年", description="后端")],
        skills=["Python", "Golang"],
        soft_skills=["沟通能力", "团队协作"]
    )
    requirements = JDRequirements(
        required_skills=["Python"],
        experience_years=3,
        education_level="本科",
        soft_skills=["沟通能力"]
    )
    
    result = matcher.match(resume, requirements)
    
    assert "hard_skills" in result
    assert "experience" in result
    assert result["hard_skills"].score == 100
```

- [ ] **Step 4: 运行测试**

```bash
cd hr-resume-match && pytest tests/test_matcher.py -v
Expected: PASS
```

- [ ] **Step 5: Commit**

```bash
cd hr-resume-match && git add -A && git commit -m "feat: 添加 Matcher 和 Scorer 模块"
```

---

## Chunk 4: Reporter 模块与 API 集成

**Files:**
- Create: `hr-resume-match/app/pipeline/reporter.py`
- Modify: `hr-resume-match/app/pipeline/__init__.py`
- Create: `hr-resume-match/app/api/routes.py`
- Create: `hr-resume-match/app/main.py`
- Test: `hr-resume-match/tests/test_reporter.py`

- [ ] **Step 1: 创建 Reporter 模块**

```python
# app/pipeline/reporter.py
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
```

- [ ] **Step 2: 创建 API 路由**

```python
# app/api/routes.py
from fastapi import APIRouter, HTTPException, Header
from app.types.models import MatchRequest, MatchReport
from app.pipeline.jd_parser import JDParser
from app.pipeline.matcher import Matcher
from app.pipeline.reporter import Reporter
import os

router = APIRouter()
parser = JDParser()
matcher = Matcher()
reporter = Reporter()

@router.post("/api/v1/match", response_model=MatchReport)
async def match_resume(
    request: MatchRequest,
    x_api_key: str = Header(None, alias="X-API-Key")
):
    api_key = os.getenv("API_KEY")
    if api_key and x_api_key != api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    try:
        requirements = parser.parse(request.job_description)
        dimension_scores = matcher.match(request.resume, requirements)
        result = reporter.generate(dimension_scores)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

- [ ] **Step 3: 创建 FastAPI 应用入口**

```python
# app/main.py
from fastapi import FastAPI
from app.api.routes import router

app = FastAPI(title="HR Resume Match API")
app.include_router(router)

@app.get("/health")
def health():
    return {"status": "ok"}
```

- [ ] **Step 4: 创建 __init__.py 文件**

```python
# app/pipeline/__init__.py
from app.pipeline.jd_parser import JDParser
from app.pipeline.matcher import Matcher
from app.pipeline.reporter import Reporter

__all__ = ["JDParser", "Matcher", "Reporter"]
```

```python
# app/api/__init__.py
from app.api.routes import router
```

```python
# app/utils/__init__.py
from app.utils.scorer import Scorer
```

- [ ] **Step 5: 编写 API 测试**

```python
# tests/test_api.py
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_match_endpoint():
    payload = {
        "resume": {
            "name": "张三",
            "education": [{"degree": "本科", "major": "计算机", "school": "清华", "year": 2018}],
            "experience": [{"company": "字节", "position": "工程师", "duration": "3年", "description": "后端"}],
            "skills": ["Python", "Golang"],
            "soft_skills": ["沟通能力"]
        },
        "job_description": "招聘Python工程师，3年以上经验，本科"
    }
    
    response = client.post("/api/v1/match", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "overall_score" in data
    assert "recommendation" in data
```

- [ ] **Step 6: 运行 API 测试**

```bash
cd hr-resume-match && pytest tests/test_api.py -v
Expected: PASS
```

- [ ] **Step 7: Commit**

```bash
cd hr-resume-match && git add -A && git commit -m "feat: 添加 Reporter 模块和 API 端点"
```

---

## Chunk 5: 错误处理完善

**Files:**
- Modify: `hr-resume-match/app/api/routes.py`

- [ ] **Step 1: 完善错误处理**

```python
# 更新 app/api/routes.py 中的错误处理
@router.post("/api/v1/match", response_model=MatchReport)
async def match_resume(
    request: MatchRequest,
    x_api_key: str = Header(None, alias="X-API-Key")
):
    api_key = os.getenv("API_KEY")
    if api_key and x_api_key != api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    if not request.job_description or len(request.job_description.strip()) < 5:
        raise HTTPException(status_code=400, detail="Job description too short")
    
    try:
        requirements = parser.parse(request.job_description)
        
        if not requirements.required_skills and requirements.experience_years == 0:
            raise HTTPException(status_code=400, detail="Unable to parse JD requirements")
        
        dimension_scores = matcher.match(request.resume, requirements)
        
        if not dimension_scores:
            raise HTTPException(status_code=500, detail="Unable to calculate scores")
        
        result = reporter.generate(dimension_scores)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=503, detail="Service temporarily unavailable")
```

- [ ] **Step 2: 运行测试验证**

```bash
cd hr-resume-match && pytest tests/ -v
Expected: PASS
```

- [ ] **Step 3: Commit**

```bash
cd hr-resume-match && git add -A && git commit -m "feat: 完善错误处理"
```

---

## 验收标准

- [ ] API 端点 `POST /api/v1/match` 可用
- [ ] 返回包含 overall_score 和 4 个维度分项评分
- [ ] 包含推荐结论和理由列表
- [ ] 错误输入返回合理错误信息
- [ ] 流水线三步骤可独立测试
- [ ] 所有测试通过

---

## 运行命令

```bash
# 安装依赖
pip install -r requirements.txt

# 启动服务
uvicorn app.main:app --reload

# 运行测试
pytest tests/ -v
```
