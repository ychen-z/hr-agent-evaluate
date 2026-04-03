# Reporter 组件文档

## 概述

`Reporter` 是 HR Agent 系统的报告生成组件,负责将多维度评分结果转换为最终的评估报告,包括综合评分、推荐结论和评估理由。它是评估流程的最后一步,将量化数据转化为可理解的决策依据。

## 核心功能

### 功能定位

**报告生成器** - 将评分数据转换为结构化报告

```
输入:                                  输出:
┌─────────────────────┐              ┌──────────────────────┐
│ DimensionScores:    │              │ MatchReport:         │
│  hard_skills: 80    │              │  overall_score: 82   │
│  experience: 100    │  ─▶ Reporter ─▶ recommendation:     │
│  education: 100     │              │    "推荐"            │
│  soft_skills: 75    │              │  reasons: [...]      │
└─────────────────────┘              │  dimensions: {...}   │
                                     └──────────────────────┘
```

## 在系统中的位置

```
评估流程:
JDParser → Matcher → Reporter → 最终报告
                       ▲
                    这里!
```

## 数据模型

### 输入

```python
dimension_scores: dict[str, DimensionScore] = {
    "hard_skills": DimensionScore(score=80, matched=[...], missing=[...]),
    "experience": DimensionScore(score=100, detail="..."),
    "education": DimensionScore(score=100, detail="..."),
    "soft_skills": DimensionScore(score=75, matched=[...], missing=[...])
}
```

### 输出

```python
class MatchReport(BaseModel):
    overall_score: int           # 综合评分 (0-100)
    dimensions: dict            # 各维度详细得分
    recommendation: str         # "推荐" 或 "不推荐"
    reasons: list[str]          # 推荐理由列表
```

## 工作原理

### 报告生成流程

```
Reporter.generate(dimension_scores)
    │
    ├─▶ 1. 计算综合评分
    │      scorer.calculate_overall()
    │      • 加权求和: 技能40% + 经验30% + 学历15% + 软技能15%
    │
    ├─▶ 2. 生成推荐结论
    │      overall >= 70 → "推荐"
    │      overall < 70  → "不推荐"
    │
    ├─▶ 3. 提取评估理由
    │      • 技术栈匹配度高 (hard_skills >= 80)
    │      • 工作经验符合要求 (experience == 100)
    │      • 教育背景符合要求 (education == 100)
    │      • 软技能匹配 (soft_skills >= 80)
    │
    └─▶ 4. 返回 MatchReport
```

### 核心算法

#### 1. 综合评分计算

```python
def calculate_overall(dimension_scores: dict) -> int:
    """
    使用加权求和计算综合评分

    权重分配:
    - 技术技能: 40%
    - 工作经验: 30%
    - 教育背景: 15%
    - 软技能: 15%
    """
    total = 0
    for dim, weight in WEIGHTS.items():
        if dim in dimension_scores:
            total += dimension_scores[dim].score * weight
    return int(total)
```

**示例**:

```python
scores = {
    "hard_skills": 80,
    "experience": 100,
    "education": 100,
    "soft_skills": 60
}

overall = 80*0.4 + 100*0.3 + 100*0.15 + 60*0.15
        = 32 + 30 + 15 + 9
        = 86
```

#### 2. 推荐阈值

```python
THRESHOLD = 70  # 推荐阈值

recommendation = "推荐" if overall >= 70 else "不推荐"
```

**设计理念**:

- 70分作为及格线
- 可根据业务需求调整阈值
- 建议范围: 60-80分

#### 3. 理由提取规则

```python
reasons = []

# 技术栈匹配度高
if hard_skills_score >= 80:
    reasons.append("技术栈匹配度高")

# 工作经验符合要求
if experience_score >= 100:
    reasons.append("工作经验符合要求")

# 教育背景符合要求
if education_score >= 100:
    reasons.append("教育背景符合要求")

# 软技能匹配
if soft_skills_score >= 80:
    reasons.append("软技能匹配")

# 兜底理由
if not reasons:
    reasons.append("综合评估结果")
```

## 使用示例

### 基本使用

```python
from app.pipeline.reporter import Reporter
from app.types.models import DimensionScore

reporter = Reporter()

# 准备维度评分
dimension_scores = {
    "hard_skills": DimensionScore(
        score=85,
        matched=["Python", "FastAPI"],
        missing=["Docker"]
    ),
    "experience": DimensionScore(
        score=100,
        detail="3年 vs 要求3年"
    ),
    "education": DimensionScore(
        score=100,
        detail="本科 vs 要求本科"
    ),
    "soft_skills": DimensionScore(
        score=50,
        matched=["沟通能力"],
        missing=["领导力"]
    )
}

# 生成报告
report = reporter.generate(dimension_scores)

print(report["overall_score"])      # 86
print(report["recommendation"])     # "推荐"
print(report["reasons"])            # ["技术栈匹配度高", "工作经验符合要求", "教育背景符合要求"]
```

### 在完整流程中使用

```python
# app/agent/tools/score_candidate.py
from app.pipeline.matcher import Matcher
from app.pipeline.reporter import Reporter

def run_score_candidate(resume: dict, requirements: dict) -> dict:
    # Step 1: 匹配评分
    matcher = Matcher()
    dimension_scores = matcher.match(resume, requirements)

    # Step 2: 生成报告
    reporter = Reporter()
    report = reporter.generate(dimension_scores)

    return report
```

## 配置选项

### 调整推荐阈值

```python
# app/pipeline/reporter.py
THRESHOLD = 75  # 提高到75分

# 或者根据岗位类型动态调整
def get_threshold(job_level: str) -> int:
    thresholds = {
        "初级": 60,
        "中级": 70,
        "高级": 80,
        "专家": 85
    }
    return thresholds.get(job_level, 70)
```

### 自定义理由规则

```python
class CustomReporter(Reporter):
    def generate(self, dimension_scores: dict) -> dict:
        overall = self.scorer.calculate_overall(dimension_scores)
        recommendation = "推荐" if overall >= THRESHOLD else "不推荐"

        # 自定义理由逻辑
        reasons = self._custom_reasons(dimension_scores, overall)

        return {
            "overall_score": overall,
            "dimensions": {k: v.model_dump() for k, v in dimension_scores.items()},
            "recommendation": recommendation,
            "reasons": reasons
        }

    def _custom_reasons(self, scores: dict, overall: int) -> list[str]:
        reasons = []

        # 更细粒度的理由
        hard = scores.get("hard_skills", DimensionScore(score=0)).score
        if hard >= 90:
            reasons.append("技能完美匹配")
        elif hard >= 80:
            reasons.append("技能匹配度高")
        elif hard >= 60:
            reasons.append("技能基本匹配")

        # ... 其他维度

        return reasons
```

## 性能考虑

### 时间复杂度

```
Reporter.generate(): O(1)
    - calculate_overall: O(4) = O(1)
    - 条件判断: O(4) = O(1)
    - 字典转换: O(4) = O(1)

极快,无性能问题
```

## 依赖关系

```
Reporter
├── app.types.models.DimensionScore
├── app.utils.scorer.Scorer
│   └── calculate_overall()
└── 常量
    └── THRESHOLD (推荐阈值)
```

## 测试

### 单元测试示例

```python
# tests/test_reporter.py
from app.pipeline.reporter import Reporter
from app.types.models import DimensionScore

def test_generate_recommend():
    """测试推荐场景"""
    reporter = Reporter()

    scores = {
        "hard_skills": DimensionScore(score=90),
        "experience": DimensionScore(score=100),
        "education": DimensionScore(score=100),
        "soft_skills": DimensionScore(score=80)
    }

    report = reporter.generate(scores)

    assert report["overall_score"] == 91  # 90*0.4 + 100*0.3 + 100*0.15 + 80*0.15
    assert report["recommendation"] == "推荐"
    assert "技术栈匹配度高" in report["reasons"]
    assert "工作经验符合要求" in report["reasons"]

def test_generate_not_recommend():
    """测试不推荐场景"""
    reporter = Reporter()

    scores = {
        "hard_skills": DimensionScore(score=50),
        "experience": DimensionScore(score=60),
        "education": DimensionScore(score=60),
        "soft_skills": DimensionScore(score=50)
    }

    report = reporter.generate(scores)

    assert report["overall_score"] == 55
    assert report["recommendation"] == "不推荐"
    assert report["reasons"] == ["综合评估结果"]  # 无其他理由

def test_edge_case_threshold():
    """测试阈值边界"""
    reporter = Reporter()

    # 恰好70分
    scores = {
        "hard_skills": DimensionScore(score=70),
        "experience": DimensionScore(score=70),
        "education": DimensionScore(score=70),
        "soft_skills": DimensionScore(score=70)
    }

    report = reporter.generate(scores)
    assert report["overall_score"] == 70
    assert report["recommendation"] == "推荐"  # >= 70
```

## 常见问题 (FAQ)

### Q1: 为什么推荐阈值是70分?

**A**:

- 70分代表"基本合格"
- 参考了行业通用标准(60分及格,70分良好)
- 可根据实际招聘标准调整

### Q2: 如何根据不同岗位设置不同阈值?

**A**: 可以扩展 Reporter 支持动态阈值:

```python
class Reporter:
    def generate(self, dimension_scores: dict, job_level: str = "中级") -> dict:
        threshold = self._get_threshold(job_level)
        overall = self.scorer.calculate_overall(dimension_scores)
        recommendation = "推荐" if overall >= threshold else "不推荐"
        # ...
```

### Q3: 理由列表为空时怎么办?

**A**: 代码中已有兜底逻辑:

```python
if not reasons:
    reasons.append("综合评估结果")
```

### Q4: 如何添加更多理由类型?

**A**: 在 `generate` 方法中添加条件判断:

```python
# 新增理由: 超出经验要求
if experience_score > 100:
    reasons.append("工作经验丰富,超出要求")

# 新增理由: 学历超标
if education_score > 100:
    reasons.append("教育背景优秀")
```

## 未来改进方向

### 1. 分级推荐

```python
def get_recommendation_level(overall: int) -> str:
    if overall >= 90:
        return "强烈推荐"
    elif overall >= 80:
        return "推荐"
    elif overall >= 70:
        return "可以考虑"
    else:
        return "不推荐"
```

### 2. 风险提示

```python
def generate_warnings(dimension_scores: dict) -> list[str]:
    warnings = []
    if dimension_scores["hard_skills"].score < 50:
        warnings.append("技能匹配度较低,可能需要额外培训")
    if dimension_scores["experience"].score < 50:
        warnings.append("工作经验不足,建议降低岗位级别")
    return warnings
```

### 3. 个性化报告模板

```python
class ReportTemplate:
    def format_reason(self, reason_type: str, score: int) -> str:
        templates = {
            "hard_skills": "技能匹配度{score}分,{level}",
            "experience": "工作经验{score}分,{level}"
        }
        # 根据分数段生成不同描述
```

### 4. 多语言支持

```python
class MultilingualReporter(Reporter):
    def __init__(self, language="zh"):
        super().__init__()
        self.language = language
        self.translations = load_translations(language)

    def generate(self, dimension_scores: dict) -> dict:
        report = super().generate(dimension_scores)
        # 翻译 recommendation 和 reasons
        return self._translate(report)
```

## 参考资料

- [Pydantic 模型验证](https://docs.pydantic.dev/)
- [Python 字典操作](https://docs.python.org/3/tutorial/datastructures.html#dictionaries)

## 维护历史

| 日期       | 版本  | 变更说明                  |
| ---------- | ----- | ------------------------- |
| 2026-04-03 | 1.0.0 | 初始版本,支持基础报告生成 |
