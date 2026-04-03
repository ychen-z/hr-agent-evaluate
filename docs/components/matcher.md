# Matcher 组件文档

## 概述

`Matcher` 是 HR Agent 系统的核心评分组件,负责将候选人简历与职位需求进行多维度匹配,计算各个维度的匹配分数。它是连接 JDParser 和 Reporter 的桥梁,在整个评估流程中处于核心位置。

## 核心功能

### 功能定位

**简历-需求匹配引擎** - 计算候选人与岗位的匹配度

```
输入:                                       输出:
┌────────────────┐                      ┌──────────────────────┐
│ Resume         │                      │ DimensionScores:     │
│ - skills       │                      │  hard_skills:        │
│ - experience   │  ─────▶ Matcher ──▶  │    score: 80         │
│ - education    │                      │    matched: [...]    │
│ - soft_skills  │                      │  experience:         │
└────────────────┘                      │    score: 100        │
┌────────────────┐                      │  education:          │
│ JDRequirements │                      │    score: 100        │
│ - required_    │                      │  soft_skills:        │
│   skills       │                      │    score: 75         │
│ - experience_  │                      └──────────────────────┘
│   years        │
│ - education_   │
│   level        │
│ - soft_skills  │
└────────────────┘
```

## 在系统中的位置

```
┌─────────────────────────────────────────────────────────┐
│                   评估流程                               │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Step 1: JDParser                                      │
│  ┌──────────────────────┐                             │
│  │ JD Text → JDRequirements                           │
│  └──────────┬───────────┘                             │
│             │                                          │
│             ▼                                          │
│  Step 2: Matcher ◄─── 这里!                           │
│  ┌──────────────────────┐                             │
│  │ Resume + Requirements                              │
│  │        ↓                                           │
│  │ 计算四个维度匹配度:                                  │
│  │  • 技术技能 (40%)                                   │
│  │  • 工作经验 (30%)                                   │
│  │  • 教育背景 (15%)                                   │
│  │  • 软技能 (15%)                                     │
│  │        ↓                                           │
│  │ → DimensionScores                                  │
│  └──────────┬───────────┘                             │
│             │                                          │
│             ▼                                          │
│  Step 3: Reporter                                     │
│  ┌──────────────────────┐                             │
│  │ Scores → MatchReport                               │
│  └──────────────────────┘                             │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

## 数据模型

### 输入

#### Resume (简历对象)

```python
class Resume(BaseModel):
    name: str
    email: Optional[str]
    phone: Optional[str]
    education: list[Education]      # 教育经历列表
    experience: list[Experience]    # 工作经历列表
    skills: list[str]               # 技术技能列表
    soft_skills: list[str]          # 软技能列表
```

#### JDRequirements (需求对象)

```python
class JDRequirements(BaseModel):
    required_skills: list[str]      # 要求的技术技能
    experience_years: int           # 要求的工作年限
    education_level: str            # 要求的学历
    soft_skills: list[str]          # 要求的软技能
```

### 输出

```python
dict[str, DimensionScore] = {
    "hard_skills": DimensionScore(
        score=80,
        matched=["Python", "FastAPI"],
        missing=["Docker"]
    ),
    "experience": DimensionScore(
        score=100,
        detail="4年 vs 要求3年"
    ),
    "education": DimensionScore(
        score=100,
        detail="本科 vs 要求本科"
    ),
    "soft_skills": DimensionScore(
        score=75,
        matched=["沟通能力"],
        missing=["领导力"]
    )
}
```

## 工作原理

### 匹配流程

```
Matcher.match(resume, requirements)
    │
    ├─▶ 1. 计算工作年限
    │      _calculate_years(experience)
    │      → 从 "3年", "2年6个月" 提取总年数
    │
    ├─▶ 2. 提取最高学历
    │      _get_highest_degree(education)
    │      → 按 博士>硕士>本科>大专 排序
    │
    ├─▶ 3. 调用 Scorer 计算各维度
    │      │
    │      ├─▶ score_hard_skills(resume.skills, required_skills)
    │      │    • 大小写不敏感匹配
    │      │    • 计算匹配率: matched/required * 100
    │      │
    │      ├─▶ score_experience(resume_years, required_years)
    │      │    • 计算达成率: actual/required * 100
    │      │    • 上限100分
    │      │
    │      ├─▶ score_education(resume_degree, required_degree)
    │      │    • 学历等级映射: 大专(2), 本科(3), 硕士(4), 博士(5)
    │      │    • 达标得100分,不达标按比例
    │      │
    │      └─▶ score_soft_skills(resume_skills, required_skills)
    │           • 精确字符串匹配
    │           • 计算匹配率: matched/required * 100
    │
    └─▶ 4. 返回维度评分字典
```

### 核心算法详解

#### 1. 技术技能匹配 (Hard Skills)

```python
def score_hard_skills(resume_skills, required_skills):
    # 大小写不敏感匹配
    resume_lower = [s.lower() for s in resume_skills]

    # 计算匹配和缺失
    matched = [s for s in required_skills if s.lower() in resume_lower]
    missing = [s for s in required_skills if s.lower() not in resume_lower]

    # 计算分数
    score = len(matched) / len(required_skills) * 100

    return DimensionScore(score=score, matched=matched, missing=missing)
```

**特点**:

- ✅ 大小写不敏感 ("python" 匹配 "Python")
- ✅ 部分匹配 (有3个中的2个得 66分)
- ✅ 记录匹配和缺失项

**示例**:

```python
resume_skills = ["Python", "FastAPI", "PostgreSQL"]
required_skills = ["Python", "FastAPI", "Docker"]

result = {
    "score": 66,  # 2/3 = 66.67
    "matched": ["Python", "FastAPI"],
    "missing": ["Docker"]
}
```

#### 2. 工作经验匹配 (Experience)

```python
def score_experience(resume_years, required_years):
    if required_years == 0:
        return DimensionScore(score=100, detail="无年限要求")

    score = min(resume_years / required_years * 100, 100)

    return DimensionScore(
        score=score,
        detail=f"{resume_years}年 vs 要求{required_years}年"
    )
```

**评分规则**:

```
实际年限 / 要求年限 * 100, 上限100分

示例:
- 3年 vs 要求3年 → 100分
- 5年 vs 要求3年 → 100分 (超出也是100)
- 2年 vs 要求3年 → 66分
- 0年 vs 要求3年 → 0分
```

**年限提取**:

```python
def _calculate_years(experiences):
    total = 0
    for exp in experiences:
        # 从 "3年" 或 "3年6个月" 提取数字
        match = re.search(r'(\d+)年', exp.duration)
        if match:
            total += int(match.group(1))
    return total
```

#### 3. 教育背景匹配 (Education)

```python
EDUCATION_LEVELS = {
    "大专": 2,
    "本科": 3,
    "硕士": 4,
    "博士": 5
}

def score_education(resume_degree, required_degree):
    actual = EDUCATION_LEVELS.get(resume_degree, 0)
    required = EDUCATION_LEVELS.get(required_degree, 0)

    if actual >= required:
        score = 100  # 达标或超标
    else:
        score = actual / required * 100  # 不达标按比例

    return DimensionScore(
        score=score,
        detail=f"{resume_degree} vs 要求{required_degree}"
    )
```

**评分示例**:

```
硕士 vs 要求本科 → 100分 (超标)
本科 vs 要求本科 → 100分 (达标)
大专 vs 要求本科 → 66分  (2/3)
本科 vs 要求硕士 → 75分  (3/4)
```

#### 4. 软技能匹配 (Soft Skills)

```python
def score_soft_skills(resume_skills, required_skills):
    # 精确字符串匹配 (区分大小写)
    matched = [s for s in required_skills if s in resume_skills]
    missing = [s for s in required_skills if s not in resume_skills]

    score = len(matched) / len(required_skills) * 100

    return DimensionScore(score=score, matched=matched, missing=missing)
```

**注意**: 软技能使用精确匹配,不做大小写转换

## 使用示例

### 基本使用

```python
from app.pipeline.matcher import Matcher
from app.types.models import Resume, JDRequirements, Education, Experience

# 创建匹配器
matcher = Matcher()

# 准备简历
resume = Resume(
    name="张三",
    email="zhangsan@example.com",
    phone="138****0000",
    education=[
        Education(degree="本科", major="计算机科学", school="清华大学", year=2018)
    ],
    experience=[
        Experience(
            company="字节跳动",
            position="Python工程师",
            duration="3年",
            description="后端开发"
        )
    ],
    skills=["Python", "FastAPI", "PostgreSQL"],
    soft_skills=["沟通能力", "团队协作"]
)

# 准备需求 (通常来自 JDParser)
requirements = JDRequirements(
    required_skills=["Python", "FastAPI", "Docker"],
    experience_years=3,
    education_level="本科",
    soft_skills=["沟通能力", "问题解决能力"]
)

# 执行匹配
dimension_scores = matcher.match(resume, requirements)

# 查看结果
print(dimension_scores["hard_skills"].score)      # 66
print(dimension_scores["hard_skills"].matched)    # ["Python", "FastAPI"]
print(dimension_scores["hard_skills"].missing)    # ["Docker"]

print(dimension_scores["experience"].score)       # 100
print(dimension_scores["education"].score)        # 100
print(dimension_scores["soft_skills"].score)      # 50
```

### 在 Agent 工具中使用

```python
# app/agent/tools/score_candidate.py
from app.pipeline.matcher import Matcher
from app.pipeline.reporter import Reporter

matcher = Matcher()
reporter = Reporter()

def run_score_candidate(resume: dict, requirements: dict) -> dict:
    # 转换为对象
    resume_obj = Resume(**resume)
    requirements_obj = JDRequirements(**requirements)

    # 匹配评分
    dimension_scores = matcher.match(resume_obj, requirements_obj)

    # 生成报告
    report = reporter.generate(dimension_scores)

    return report
```

## 辅助方法

### \_calculate_years()

**作用**: 从工作经历列表中提取总工作年限

```python
def _calculate_years(self, experiences: list) -> int:
    total = 0
    for exp in experiences:
        # 正则匹配 "X年"
        match = re.search(r'(\d+)年', exp.duration)
        if match:
            total += int(match.group(1))
    return total
```

**支持的格式**:

- ✅ "3年" → 3
- ✅ "3年6个月" → 3 (忽略月份)
- ✅ "5年2个月" → 5
- ❌ "36个月" → 0 (不支持)
- ❌ "Three years" → 0 (不支持英文)

### \_get_highest_degree()

**作用**: 从教育经历列表中提取最高学历

```python
def _get_highest_degree(self, education: list) -> str:
    degrees = [e.degree for e in education]
    priority = ["博士", "硕士", "本科", "大专"]

    # 按优先级查找
    for d in priority:
        if d in degrees:
            return d

    # 默认本科
    return "本科"
```

**示例**:

```python
education = [
    Education(degree="本科", ...),
    Education(degree="硕士", ...)
]
# 返回: "硕士"

education = [
    Education(degree="大专", ...)
]
# 返回: "大专"

education = []
# 返回: "本科" (默认)
```

## 评分权重

Matcher 使用 `Scorer` 类计算综合分数时的权重分配:

```python
WEIGHTS = {
    "hard_skills": 0.4,    # 40% - 技术技能最重要
    "experience": 0.3,     # 30% - 工作经验其次
    "education": 0.15,     # 15% - 教育背景
    "soft_skills": 0.15    # 15% - 软技能
}

overall_score = (
    hard_skills_score * 0.4 +
    experience_score * 0.3 +
    education_score * 0.15 +
    soft_skills_score * 0.15
)
```

**权重设计理念**:

- 技术岗位以技能和经验为主
- 教育背景和软技能为辅助参考
- 可根据不同岗位类型调整权重

## 性能考虑

### 时间复杂度

```
matcher.match(resume, requirements):
    O(n*m) where:
    - n = len(resume.skills)
    - m = len(required_skills)

实际场景:
    n ≈ 10, m ≈ 5
    → O(50) 非常快
```

### 优化建议

#### 1. 技能匹配优化

```python
# 当前: O(n*m)
matched = [s for s in required_skills if s.lower() in resume_lower]

# 优化: O(n+m)
resume_set = set(s.lower() for s in resume_skills)
matched = [s for s in required_skills if s.lower() in resume_set]
```

#### 2. 批量匹配

```python
class Matcher:
    def match_batch(self, resumes: list[Resume], requirements: JDRequirements) -> list[dict]:
        """批量处理多个简历"""
        return [self.match(resume, requirements) for resume in resumes]
```

#### 3. 缓存常用计算

```python
from functools import lru_cache

class Matcher:
    @lru_cache(maxsize=100)
    def _calculate_years_cached(self, experiences_tuple: tuple) -> int:
        """缓存年限计算结果"""
        experiences = list(experiences_tuple)
        return self._calculate_years(experiences)
```

## 依赖关系

```
Matcher
├── app.types.models
│   ├── Resume
│   ├── JDRequirements
│   └── DimensionScore
├── app.utils.scorer.Scorer
│   ├── score_hard_skills()
│   ├── score_experience()
│   ├── score_education()
│   └── score_soft_skills()
└── Python 标准库
    └── re (正则表达式)
```

## 测试

### 单元测试示例

```python
# tests/test_matcher.py
import pytest
from app.pipeline.matcher import Matcher
from app.types.models import Resume, JDRequirements, Education, Experience

def test_match_perfect_candidate():
    """测试完美匹配的候选人"""
    matcher = Matcher()

    resume = Resume(
        name="测试",
        education=[Education(degree="本科", major="CS", school="清华", year=2018)],
        experience=[Experience(company="A", position="工程师", duration="3年", description="开发")],
        skills=["Python", "FastAPI", "Docker"],
        soft_skills=["沟通能力", "团队协作"]
    )

    requirements = JDRequirements(
        required_skills=["Python", "FastAPI", "Docker"],
        experience_years=3,
        education_level="本科",
        soft_skills=["沟通能力", "团队协作"]
    )

    scores = matcher.match(resume, requirements)

    assert scores["hard_skills"].score == 100
    assert scores["experience"].score == 100
    assert scores["education"].score == 100
    assert scores["soft_skills"].score == 100

def test_match_partial_skills():
    """测试部分技能匹配"""
    matcher = Matcher()

    resume = Resume(
        name="测试",
        education=[Education(degree="本科", major="CS", school="清华", year=2018)],
        experience=[Experience(company="A", position="工程师", duration="3年", description="开发")],
        skills=["Python", "FastAPI"],  # 缺少 Docker
        soft_skills=[]
    )

    requirements = JDRequirements(
        required_skills=["Python", "FastAPI", "Docker"],
        experience_years=3,
        education_level="本科",
        soft_skills=[]
    )

    scores = matcher.match(resume, requirements)

    assert scores["hard_skills"].score == 66  # 2/3
    assert scores["hard_skills"].matched == ["Python", "FastAPI"]
    assert scores["hard_skills"].missing == ["Docker"]

def test_calculate_years():
    """测试年限计算"""
    matcher = Matcher()

    experiences = [
        Experience(company="A", position="工程师", duration="3年", description="开发"),
        Experience(company="B", position="高级工程师", duration="2年6个月", description="架构")
    ]

    total_years = matcher._calculate_years(experiences)
    assert total_years == 5  # 3 + 2

def test_get_highest_degree():
    """测试最高学历提取"""
    matcher = Matcher()

    education = [
        Education(degree="本科", major="CS", school="A大学", year=2015),
        Education(degree="硕士", major="CS", school="B大学", year=2018)
    ]

    highest = matcher._get_highest_degree(education)
    assert highest == "硕士"
```

## 常见问题 (FAQ)

### Q1: 为什么技术技能匹配是大小写不敏感的,但软技能不是?

**A**:

- **技术技能**: 通常是缩写或专有名词,大小写变体多 ("python", "Python", "PYTHON")
- **软技能**: 通常是完整词组,格式统一 ("沟通能力", "团队协作")
- 如需统一,可以修改 `score_soft_skills` 方法

### Q2: 如何调整各维度的权重?

**A**: 修改 `Scorer` 类的 `WEIGHTS` 字典:

```python
# app/utils/scorer.py
WEIGHTS = {
    "hard_skills": 0.5,    # 提高技术技能权重到50%
    "experience": 0.3,
    "education": 0.1,
    "soft_skills": 0.1
}
```

### Q3: 年限计算不支持"月"怎么办?

**A**: 可以改进 `_calculate_years` 方法:

```python
def _calculate_years(self, experiences: list) -> float:
    total_months = 0
    for exp in experiences:
        # 匹配 "X年Y个月"
        year_match = re.search(r'(\d+)年', exp.duration)
        month_match = re.search(r'(\d+)个月', exp.duration)

        if year_match:
            total_months += int(year_match.group(1)) * 12
        if month_match:
            total_months += int(month_match.group(1))

    return total_months / 12  # 转换为年
```

### Q4: 如何处理同义技能?

**A**: 可以引入技能映射表:

```python
SKILL_SYNONYMS = {
    "js": "javascript",
    "ts": "typescript",
    "py": "python",
    "k8s": "kubernetes"
}

def normalize_skill(skill: str) -> str:
    lower = skill.lower()
    return SKILL_SYNONYMS.get(lower, lower)
```

### Q5: 如何支持技能的模糊匹配?

**A**: 可以使用字符串相似度算法:

```python
from difflib import SequenceMatcher

def fuzzy_match(skill1: str, skill2: str, threshold=0.8) -> bool:
    ratio = SequenceMatcher(None, skill1.lower(), skill2.lower()).ratio()
    return ratio >= threshold
```

## 未来改进方向

### 1. 支持技能等级

```python
class Skill(BaseModel):
    name: str
    level: int  # 1-5级

# 匹配时考虑等级差异
def score_hard_skills_with_level(resume_skills, required_skills):
    # Python(3级) vs 要求Python(5级) → 部分分数
    pass
```

### 2. 支持技能分类

```python
class SkillCategory(BaseModel):
    programming: list[str]      # 编程语言
    frameworks: list[str]       # 框架
    databases: list[str]        # 数据库
    tools: list[str]            # 工具

# 不同类别使用不同权重
```

### 3. 引入 NLP 相似度匹配

```python
from sentence_transformers import SentenceTransformer

class SemanticMatcher(Matcher):
    def __init__(self):
        super().__init__()
        self.model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

    def score_hard_skills_semantic(self, resume_skills, required_skills):
        # 使用语义相似度而非精确匹配
        # "后端开发" 能匹配 "服务端开发"
        pass
```

### 4. 支持行业特定评分规则

```python
class TechMatcher(Matcher):
    """技术岗位专用匹配器"""
    WEIGHTS = {"hard_skills": 0.5, "experience": 0.35, ...}

class SalesMatcher(Matcher):
    """销售岗位专用匹配器"""
    WEIGHTS = {"soft_skills": 0.4, "experience": 0.4, ...}
```

## 参考资料

- [正则表达式文档](https://docs.python.org/3/library/re.html)
- [Pydantic 数据验证](https://docs.pydantic.dev/)
- [模糊字符串匹配](https://docs.python.org/3/library/difflib.html)

## 维护历史

| 日期       | 版本  | 变更说明                |
| ---------- | ----- | ----------------------- |
| 2026-04-03 | 1.0.0 | 初始版本,支持四维度匹配 |
