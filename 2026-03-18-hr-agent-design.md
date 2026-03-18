# HR 简历-JD 匹配评估 Agent 设计文档

**日期**: 2026-03-18  
**主题**: 简历与JD匹配度评估

---

## 1. 概述

HR 评估 Agent 是一个基于 NLP 的简历与职位描述（JD）匹配度评估系统。系统接收结构化简历数据和 JD 文本，输出多维度匹配评分及推荐理由。

---

## 2. 架构设计

```
┌─────────────┐    ┌──────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   API       │───▶│   JD Parser  │───▶│   Matcher       │───▶│   Reporter      │
│   Input     │    │   (Step 1)   │    │   (Step 2)      │    │   (Step 3)      │
└─────────────┘    └──────────────┘    └─────────────────┘    └─────────────────┘
                       │                     │                      │
                       ▼                     ▼                      ▼
                  JD Requirements      Dimension              Final Report
                  (structured)         Scores
```

### 2.1 输入格式

**API 端点**: `POST /api/v1/match`  
**认证方式**: API Key (Header: `X-API-Key`)

**API Request:**
```json
{
  "resume": {
    "name": "张三",
    "email": "zhangsan@example.com",
    "phone": "13800138000",
    "education": [
      {
        "degree": "本科",
        "major": "计算机科学",
        "school": "清华大学",
        "year": 2018
      }
    ],
    "experience": [
      {
        "company": "字节跳动",
        "position": "高级工程师",
        "duration": "3年",
        "description": "负责推荐系统后端开发，使用Python、Golang"
      }
    ],
    "skills": ["Python", "Golang", "React", "MySQL", "Redis"],
    "soft_skills": ["沟通能力", "团队协作"]
  },
  "job_description": "招聘高级后端工程师，要求熟练掌握Python或Golang，有3年以上后端开发经验，本科以上学历，具备良好的沟通能力和团队协作精神。"
}
```

### 2.2 输出格式

**API Response:**
```json
{
  "overall_score": 85,
  "dimensions": {
    "hard_skills": {
      "score": 90,
      "matched": ["Python", "Golang"],
      "missing": []
    },
    "experience": {
      "score": 100,
      "actual_years": 3,
      "required_years": 3,
      "detail": "3年 vs 要求3年"
    },
    "education": {
      "score": 100,
      "actual_degree": "本科",
      "required_degree": "本科",
      "detail": "本科 vs 要求本科"
    },
    "soft_skills": {
      "score": 75,
      "matched": ["沟通能力", "团队协作"],
      "missing": []
    }
  },
  "recommendation": "推荐",
  "reasons": [
    "技术栈匹配度高",
    "工作经验符合要求",
    "教育背景符合要求",
    "软技能匹配"
  ]
}
```

---

## 3. 流水线处理流程

### Step 1: JD Parser

从 JD 文本中提取结构化需求：

| 字段 | 提取内容 | 方法 |
|------|----------|------|
| required_skills | 技术栈要求 | NLP实体识别 |
| experience_years | 工作年限 | 正则 + NLP |
| education_level | 学历要求 | 规则匹配 |
| soft_skills | 软技能要求 | NLP关键词提取 |

### Step 2: Matcher

对每个维度进行独立评分：

| 维度 | 评分逻辑 | 权重 |
|------|----------|------|
| hard_skills | 技能匹配数量/总数 × 100，上限100 | 40% |
| experience | 实际年限/要求年限 × 100，上限100 | 30% |
| education | 学历等级匹配（大专=2，本科=3，硕士=4，博士=5）实际≥要求=100，否则按比例 | 15% |
| soft_skills | 软技能匹配数量/总数 × 100，上限100 | 15% |

**总分计算**:
```
overall_score = hard_skills × 0.4 + experience × 0.3 + education × 0.15 + soft_skills × 0.15
```

### Step 3: Reporter

生成最终报告：
- 推荐结论：总分 ≥ 70 为"推荐"，< 70 为"不推荐"
- 匹配理由：列出匹配的维度
- 缺失项：列出未匹配的维度

---

## 4. 技术实现

### 4.1 技术栈

- **运行时**: Python 3.10+
- **NLP能力**: Claude API (Anthropic)
- **API框架**: FastAPI

### 4.2 模块设计

```
src/
├── api/
│   └── handler.py           # API入口
├── pipeline/
│   ├── jd_parser.py         # JD解析
│   ├── matcher.py           # 匹配计算
│   └── reporter.py          # 报告生成
├── types/
│   └── __init__.py          # 类型定义
└── utils/
    └── scorer.py            # 评分工具
```

---

## 5. 错误处理

| 场景 | 处理方式 |
|------|----------|
| 简历格式缺失必填字段 | 返回400错误，提示缺少字段 |
| JD为空或过短 | 返回错误提示 |
| LLM调用失败 | 返回503，提示服务暂时不可用 |
| 评分维度数据异常 | 跳过该维度，总分按可用维度重新计算 |

### 5.1 边界情况

| 场景 | 处理方式 |
|------|----------|
| JD解析失败 | 返回错误，提示JD格式无法解析 |
| 所有维度都被跳过 | 返回错误，提示无法进行评估 |
| 推荐阈值 | 70分为默认值，不可配置 |

---

## 6. 验收标准

- [ ] API可接收结构化简历+JD，返回完整匹配报告
- [ ] 输出包含overall_score和4个维度分项评分
- [ ] 包含推荐结论和理由列表
- [ ] 错误输入返回合理错误信息
- [ ] 流水线三步骤可独立测试

---

## 7. 后续优化（暂不实现）

- 预设岗位库管理
- 评估历史记录存储
- 自定义权重配置
- 多语言支持
