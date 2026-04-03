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

---

## AI 增强评分

### 概述

从 **v1.1.0** 版本开始,Matcher 支持 **AI 增强评分模式**,使用 LLM 进行深度候选人评估,显著提升评分的准确性和智能化程度。

### 设计理念

AI 增强评分采用 **混合架构**,结合算法的确定性和 AI 的灵活性:

```
┌───────────────────────────────────────────────────────────┐
│              混合评分架构 (AI 主导 + 算法基准)              │
├───────────────────────────────────────────────────────────┤
│                                                           │
│  Phase 1: 算法预评分 (快速,确定性)                       │
│  ┌─────────────────────────────────────────────────┐     │
│  │  Matcher.match(resume, requirements)            │     │
│  │  • 技能: 字符串匹配 → 基准分 60                  │     │
│  │  • 经验: 年限比较 → 基准分 100                   │     │
│  │  • 学历: 等级映射 → 基准分 100                   │     │
│  │  • 软技能: 字符串匹配 → 基准分 33                │     │
│  └─────────────────────────────────────────────────┘     │
│                    ↓                                      │
│                                                           │
│  Phase 2: AI 深度评估 (1次 LLM 调用)                     │
│  ┌─────────────────────────────────────────────────┐     │
│  │  AIEnhancedMatcher._ai_evaluate()               │     │
│  │                                                 │     │
│  │  输入:                                          │     │
│  │  • 完整简历 (JSON)                              │     │
│  │  • 完整需求 (JSON)                              │     │
│  │  • 算法基准分 (参考)                            │     │
│  │                                                 │     │
│  │  AI 任务:                                       │     │
│  │  ┌─────────────────────────────────────────┐   │     │
│  │  │ 1. 技能语义理解                         │   │     │
│  │  │    React ≈ Vue (相似前端框架)          │   │     │
│  │  │    从项目推断技能深度                   │   │     │
│  │  │                                         │   │     │
│  │  │ 2. 经验质量评估                         │   │     │
│  │  │    项目复杂度 (高并发/分布式)          │   │     │
│  │  │    职责深度 (架构 > 开发)              │   │     │
│  │  │                                         │   │     │
│  │  │ 3. 软技能推断                           │   │     │
│  │  │    带团队 → 领导力                      │   │     │
│  │  │    跨部门 → 沟通协作                    │   │     │
│  │  │                                         │   │     │
│  │  │ 4. 输出调整后评分                       │   │     │
│  │  │    技能: 85 (+25, 识别相关技能)        │   │     │
│  │  │    经验: 100 (无调整)                   │   │     │
│  │  │    学历: 100 (无调整)                   │   │     │
│  │  │    软技能: 70 (+37, 从经历推断)        │   │     │
│  │  └─────────────────────────────────────────┘   │     │
│  └─────────────────────────────────────────────────┘     │
│                    ↓                                      │
│                                                           │
│  Phase 3: 优雅降级 (错误处理)                            │
│  ┌─────────────────────────────────────────────────┐     │
│  │  if LLM 失败:                                   │     │
│  │      记录警告日志                               │     │
│  │      返回算法基准分 (保证可用性)                │     │
│  └─────────────────────────────────────────────────┘     │
│                                                           │
└───────────────────────────────────────────────────────────┘
```

### 核心优势

| 维度 | 传统算法 | AI 增强 |
|------|---------|---------|
| **技能匹配** | 字符串精确匹配,遗漏相似技能 | 语义理解,识别 React ≈ Vue,Python 生态完整性 |
| **经验评估** | 只看年限 (3年=100分) | 看质量,项目复杂度,职责深度 |
| **软技能** | 依赖明确列出 | 从经历推断 (带团队→领导力) |
| **可解释性** | 无 | 详细推理说明 + 亮点 + 关注点 |
| **成本** | 免费 | ~¥0.042/候选人 |
| **速度** | ~0.1秒 | ~3秒 (含 LLM) |

### 启用方式

通过环境变量一键启用:

```bash
# .env 文件
USE_AI_ENHANCED_MATCHER=true
```

代码会自动切换:

```python
# app/agent/tools/score_candidate.py
use_ai_enhanced = os.getenv("USE_AI_ENHANCED_MATCHER", "false").lower() == "true"

if use_ai_enhanced:
    matcher = AIEnhancedMatcher()  # AI 增强
else:
    matcher = Matcher()            # 传统算法
```

### AI Prompt 设计

完整的 Prompt 包含 **200+ 行**,核心结构:

```
你是一位资深的技术招聘专家,拥有15年的HR和技术背景。

【岗位需求】(JSON)
【候选人简历】(JSON)
【算法基准分】(供参考)

【评估要求】
1. 技术技能匹配度 (40%权重)
   - 语义相似性 (React vs Vue)
   - 技能深度推断 (从项目经历)
   - 技能生态完整性
   - 可迁移技能

2. 工作经验质量 (30%权重)
   - 相关性和质量 (不只看年限)
   - 项目复杂度
   - 职责深度
   - 识别水分

3. 教育背景 (15%权重)
   - 学历等级
   - 专业相关性
   - 学校背景

4. 软技能与潜力 (15%权重)
   - 从经历推断软技能
   - 学习能力
   - 成长潜力
   - 稳定性

【输出格式】
严格 JSON,包含:
{
  "dimensions": {
    "hard_skills": {
      "score": 85,
      "baseline": 60,
      "adjustment_reasoning": "详细说明...",
      "highlights": ["亮点1", "亮点2"],
      "concerns": ["关注点1"]
    },
    ...
  },
  "overall_assessment": {...}
}

【重要提示】
- 客观公正
- 引用简历具体内容
- 识别暗示信息
- 基准分仅供参考
```

完整 Prompt 见: `app/pipeline/matcher.py` 中的 `AI_EVALUATION_PROMPT` 常量

### 输出示例

AI 增强评分的输出包含更多字段:

```python
{
  "hard_skills": {
    "score": 85,                    # AI 调整后的分数
    "baseline_score": 60,           # 算法基准分
    "matched": ["Python", "FastAPI"],
    "missing": ["Docker"],
    "adjustment_reasoning": "候选人虽然简历只列出Python和FastAPI,但项目经历显示其使用了Django、Celery、Redis等完整技术栈,说明技能深度较高。虽未明确列出Docker,但在项目中有容器化部署经验,实际掌握程度较好。算法基准分60分主要是字符串匹配遗漏了相关技能,综合评估应为85分。",
    "highlights": [
      "技术栈完整",
      "有架构经验"
    ],
    "concerns": [
      "缺少云原生经验"
    ]
  },
  "experience": {
    "score": 90,
    "baseline_score": 100,
    "detail": "3年 vs 要求3年",
    "adjustment_reasoning": "候选人3年经验满足要求,但深入分析发现其项目规模较大(日活百万级),且负责核心模块架构设计,经验质量较高。虽然年限刚好达标,但经验含金量超出一般3年工程师,给予90分。",
    "highlights": [
      "高并发经验",
      "架构设计能力"
    ],
    "concerns": []
  },
  ...
}
```

### 成本与性能

#### 成本估算

基于 MiniMax M2.5 定价 (¥0.015/1K tokens):

```
每个候选人:
  输入 tokens:  ~2000 (简历 + 需求 + prompt)
  输出 tokens:  ~800  (评估结果)
  
  成本 = (2000 + 800) × 0.015 / 1000
       = ¥0.042 (~$0.006)
```

**月度成本示例**:
- 评估 100 个候选人: ~¥4.2
- 评估 1000 个候选人: ~¥42
- 评估 10000 个候选人: ~¥420

#### 性能对比

| 指标 | 传统算法 | AI 增强 |
|------|---------|---------|
| 响应时间 | ~0.1秒 | ~3秒 |
| LLM 调用 | 0次 | 1次 |
| 准确性 | 中等 | 高 |
| 可解释性 | 低 | 高 |

### 降级策略

当 LLM 调用失败时,系统自动降级到算法评分:

```python
def match(self, resume, requirements):
    # Step 1: 获取算法基准分
    baseline_scores = super().match(resume, requirements)
    
    # Step 2: 尝试 AI 评估
    try:
        ai_scores = self._ai_evaluate(...)
        return ai_scores
    except Exception as e:
        # Step 3: 降级到算法基准分
        logger.warning(f"AI evaluation failed, using baseline: {e}")
        return baseline_scores  # ✅ 保证系统可用性
```

**降级场景**:
- LLM API 超时 (>10秒)
- LLM 返回格式错误 (JSON 解析失败)
- API Key 失效 (401 Unauthorized)
- 网络故障

### 实施案例

#### 案例 1: 识别相似技能

**场景**: 候选人会 Vue,岗位要求 React

**算法评分**:
```python
required = ["React"]
candidate = ["Vue"]
matched = []  # 无匹配
score = 0 / 1 * 100 = 0分
```

**AI 增强评分**:
```python
score = 75分
reasoning = "Vue 和 React 都是主流前端框架,核心概念相通(组件化、状态管理),技能可迁移。候选人有 Vue 经验,学习 React 成本低,给予 75 分。"
highlights = ["前端框架经验", "技能可迁移"]
```

---

#### 案例 2: 评估经验质量

**场景**: 两个候选人都是 3 年经验

**候选人 A**:
```
经验: "3年,负责企业内部管理系统维护"
算法评分: 100分 (3年 = 100%)
AI 评分: 70分
reasoning: "年限满足要求,但项目复杂度较低,主要是CRUD操作和系统维护,缺少架构设计和技术挑战。"
```

**候选人 B**:
```
经验: "3年,负责日活百万级电商系统架构设计"
算法评分: 100分 (3年 = 100%)
AI 评分: 95分
reasoning: "年限满足要求,且项目规模大(百万级用户),负责架构设计,涉及高并发、分布式等技术挑战,经验质量远超一般3年工程师。"
highlights: ["高并发经验", "架构设计能力", "大规模系统"]
```

---

#### 案例 3: 推断软技能

**场景**: 候选人简历未明确列出"领导力"

**算法评分**:
```python
required = ["沟通能力", "团队协作", "领导力"]
candidate = ["沟通能力"]
matched = ["沟通能力"]
score = 1 / 3 * 100 = 33分
```

**AI 增强评分**:
```python
score = 70分
reasoning = "简历明确提到'沟通能力',但未列出'团队协作'和'领导力'。然而从工作经历看,候选人在某项目中'负责前后端协作对接'(体现沟通和协作能力),且'指导2名初级工程师'(体现领导力潜质)。算法基准分33分过低,综合推断应为70分。"
highlights = ["有指导他人经验", "跨团队协作能力"]
concerns = ["领导经验有限,仅指导过2人"]
```

### 对比其他方案

在设计 AI 增强评分时,我们评估了 4 种方案:

#### 方案 A: AI 增强现有算法 (渐进式)

```
算法评分 → AI 微调 → 最终分数
  60分       +10分       70分
```

**优势**: 改动小,风险低  
**劣势**: AI 受限于算法框架,无法发挥全部潜力  
**结论**: ❌ 未采用

---

#### 方案 B: AI 作为独立维度 ⭐ (已采用)

```
原有4维度 (70%权重) + AI综合评估 (30%权重)
```

**优势**: 
- AI 和算法各司其职,互补
- 算法提供基准,AI 提供深度
- 降级策略简单 (LLM失败用算法)

**劣势**: 权重分配需调优  
**结论**: ✅ **已采用** (实际实现中 AI 主导,算法作为基准和兜底)

---

#### 方案 C: AI 完全接管 (激进式)

```
只用 AI 评分,算法结果仅作为输入参考
```

**优势**: 最灵活,最智能  
**劣势**: 
- 可解释性差
- 成本高
- 稳定性待验证
- 无兜底方案

**结论**: ❌ 未采用 (风险过高)

---

#### 方案 D: 混合专家系统 (最优解?)

```
不同维度使用不同策略:
- 技能: AI增强算法
- 经验: 纯AI评估
- 学历: 纯算法
- 软技能: 纯AI推断
```

**优势**: 各取所长,实用主义  
**劣势**: 实现复杂度高  
**结论**: 🔮 未来可考虑

---

### 最终选择: 方案 B 变体

我们采用的实际是 **方案 B 的变体**:

```
Matcher (算法基准) → AIEnhancedMatcher (AI 主导 + 算法兜底)
```

**关键特点**:
1. ✅ AI **主导**评分 (而非辅助)
2. ✅ 算法提供**基准分**供 AI 参考
3. ✅ 算法作为**兜底** (LLM 失败时降级)
4. ✅ 单次 LLM 调用 (成本可控)
5. ✅ 详细推理说明 (可解释)

### 使用建议

#### 何时启用 AI 增强?

**推荐启用**:
- ✅ 技术岗位招聘 (技能复杂度高)
- ✅ 中高级岗位 (需要深度评估)
- ✅ 候选人简历复杂 (需要综合判断)
- ✅ 对评估质量要求高
- ✅ 可接受 ~3秒响应时间

**可不启用**:
- ❌ 初级岗位 (标准化程度高)
- ❌ 大批量筛选 (成本考虑)
- ❌ 对响应时间要求极高 (<1秒)
- ❌ LLM API 不稳定

#### 灰度发布策略

**阶段 1: 内部测试**
```bash
# 开发环境启用
USE_AI_ENHANCED_MATCHER=true
```
对比 AI 和算法评分结果,验证准确性

**阶段 2: 小范围试用**
```python
# 按候选人 ID 灰度
if candidate_id % 10 < 3:  # 30% 流量
    use_ai = True
```

**阶段 3: 全面推广**
```bash
# 生产环境启用
USE_AI_ENHANCED_MATCHER=true
```

#### 监控指标

建议监控以下指标:

| 指标 | 说明 | 目标 |
|------|------|------|
| **成功率** | AI 评估成功 / 总请求 | >99% |
| **响应时间** | P50 / P95 / P99 | <3s / <5s / <8s |
| **降级率** | LLM 失败降级次数 / 总请求 | <1% |
| **成本** | 月度 LLM 调用费用 | 按预算控制 |
| **准确性** | HR 反馈的评分准确性 | 主观评估 |

### 常见问题

#### Q1: AI 评分会不会不稳定?

**A**: 有一定波动,但可接受:
- Prompt 中强调"客观评估"
- 提供算法基准分作为锚点
- 记录每次评估的推理过程,便于审计
- 后续可考虑添加结果缓存 (相同简历+JD返回相同结果)

---

#### Q2: 成本会不会失控?

**A**: 可控:
- 单次调用评估所有维度 (不是4次调用)
- 每候选人 ~¥0.042,即使评估1000人也只需 ~¥42
- 可设置月度预算上限
- 超预算时自动降级到算法评分

---

#### Q3: 如何验证 AI 评分的准确性?

**A**: 多种方式:
1. **A/B 测试**: 对比 AI 和算法评分的 HR 满意度
2. **人工抽查**: 定期抽查 AI 评分结果,与 HR 判断对比
3. **推理审计**: 检查 AI 的 `adjustment_reasoning`,看是否合理
4. **Offer 接受率**: 跟踪推荐候选人的最终录用率

---

#### Q4: LLM 失败频率高怎么办?

**A**: 排查步骤:
1. 检查 API Key 是否有效
2. 检查网络连接
3. 查看 LLM 服务商状态页
4. 考虑切换到更稳定的 LLM 提供商
5. 临时关闭 AI 增强: `USE_AI_ENHANCED_MATCHER=false`

---

#### Q5: 能否自定义 Prompt?

**A**: 可以,但需修改代码:
```python
# app/pipeline/matcher.py
AI_EVALUATION_PROMPT = """
你的自定义 Prompt...
"""
```

未来可考虑支持:
- 不同岗位类型使用不同 Prompt 模板
- 通过配置文件管理 Prompt
- Prompt 版本管理和 A/B 测试

### 技术细节

#### LLM 客户端

AI 增强评分使用统一的 `LLMClient`:

```python
# app/utils/llm_client.py
class LLMClient:
    def invoke(self, prompt: str, expect_json: bool = True):
        # 调用 LLM
        response = self.model.invoke([HumanMessage(content=prompt)])
        
        # 解析 JSON (支持 markdown 代码块)
        if expect_json:
            return self._extract_json(response.content)
        
        return response.content
```

支持多种 JSON 格式:
- ` ```json {...} ``` `
- ` ``` {...} ``` `
- 文本中嵌入的 `{...}`

#### 数据流

```python
# 1. 构建 Prompt
prompt = self._build_prompt(resume, requirements, baseline_scores)

# 2. 调用 LLM
response_data = self.llm_client.invoke(prompt, expect_json=True)
# response_data = {
#   "dimensions": {...},
#   "overall_assessment": {...}
# }

# 3. 解析为 DimensionScore
ai_scores = self._parse_ai_response(response_data, baseline_scores)
# ai_scores = {
#   "hard_skills": DimensionScore(score=85, baseline_score=60, ...),
#   ...
# }

# 4. Reporter 使用 ai_scores 生成报告
report = reporter.generate(ai_scores)
```

### 未来改进

#### 1. 多模型支持

```python
# 支持切换不同 LLM
USE_AI_MODEL=gpt-4  # 或 claude-3, qwen-plus
```

#### 2. Prompt 优化

- 持续优化 Prompt 以提高准确性
- 不同岗位类型使用不同 Prompt
- Prompt 版本管理

#### 3. 结果缓存

```python
from cachetools import TTLCache

_evaluation_cache = TTLCache(maxsize=1000, ttl=3600)

def _ai_evaluate(self, resume, requirements, baseline):
    cache_key = hash((resume.model_dump_json(), requirements.model_dump_json()))
    if cache_key in _evaluation_cache:
        return _evaluation_cache[cache_key]
    # ...
```

#### 4. 评分解释可视化

在 HTML 报告中展示:
- AI 的推理过程
- 算法基准分 vs AI 调整后分数的对比
- 亮点和关注点的可视化

#### 5. 用户反馈循环

```python
# 记录 HR 对 AI 评分的反馈
@app.post("/api/v1/feedback")
def submit_feedback(session_id: str, rating: int, comment: str):
    # 用于后续优化 Prompt 和模型
    pass
```

### 参考资料

- [LangChain 文档](https://python.langchain.com/)
- [Prompt Engineering Guide](https://www.promptingguide.ai/)
- [MiniMax API 文档](https://www.minimaxi.com/document)

---

## 维护历史

| 日期       | 版本  | 变更说明                |
| ---------- | ----- | ----------------------- |
| 2026-04-03 | 1.0.0 | 初始版本,基础算法评分   |
| 2026-04-03 | 1.1.0 | 新增 AI 增强评分功能    |
