# Tools 组件文档

## 概述

`Tools` 模块包含三个核心工具函数,供 HRAgent 调用完成简历评估流程。每个工具都使用 `@traced_tool` 装饰器进行日志追踪。

## 工具列表

```
app/agent/tools/
├── parse_jd.py             # 解析职位描述
├── score_candidate.py      # 评分候选人
└── generate_report_html.py # 生成 HTML 报告
```

## 1. parse_jd

### 功能
解析职位描述文本,提取结构化需求信息。

### 位置
`app/agent/tools/parse_jd.py`

### 签名
```python
@traced_tool("parse_jd")
@tool
def parse_jd(jd_text: str) -> str:
    """解析职位描述,返回 JSON 字符串"""
```

### 输入
- `jd_text` (str): 职位描述文本

### 输出
```json
{
  "technical_skills": ["Python", "FastAPI"],
  "years_of_experience": 3,
  "education_required": "本科",
  "soft_skills": ["沟通能力", "团队协作"]
}
```

### 实现
```python
def run_parse_jd(jd_text: str) -> dict:
    """实际执行解析"""
    parser = JDParser()
    requirements = parser.parse(jd_text)
    return requirements.model_dump()
```

### 日志输出
```
[parse_jd] START Input: "招聘Python工程师，3年经验..."
[parse_jd] END Duration: 2134.56ms Status: success Output: {"technical_skills": [...]}
```

### 错误处理
```python
try:
    requirements = parser.parse(jd_text)
except Exception as e:
    logger.error(f"Failed to parse JD: {e}")
    raise ToolException(f"JD parsing error: {e}") from e
```

---

## 2. score_candidate

### 功能
评估候选人与需求的匹配度,返回多维度评分报告。

### 位置
`app/agent/tools/score_candidate.py`

### 签名
```python
@traced_tool("score_candidate")
@tool
def score_candidate(resume: dict, requirements: dict) -> str:
    """评分候选人,返回 JSON 字符串"""
```

### 输入
- `resume` (dict): 候选人简历对象 (序列化)
- `requirements` (dict): 职位需求对象 (序列化)

### 输出
```json
{
  "overall_score": 86,
  "dimensions": {
    "hard_skills": {
      "score": 85,
      "matched": ["Python", "FastAPI"],
      "missing": ["Docker"]
    },
    "experience": {
      "score": 100,
      "detail": "3年 vs 要求3年"
    },
    "education": {
      "score": 100,
      "detail": "本科 vs 要求本科"
    },
    "soft_skills": {
      "score": 50,
      "matched": ["沟通能力"],
      "missing": ["团队协作"]
    }
  },
  "recommendation": "推荐",
  "reasons": ["技术栈匹配度高", "工作经验符合要求", "教育背景符合要求"]
}
```

### 实现
```python
def run_score_candidate(resume: dict, requirements: dict) -> dict:
    """实际执行评分"""
    # 1. 反序列化
    resume_obj = Resume(**resume)
    requirements_obj = Requirements(**requirements)
    
    # 2. 匹配评分
    matcher = Matcher()
    dimension_scores = matcher.match(resume_obj, requirements_obj)
    
    # 3. 生成报告
    reporter = Reporter()
    report = reporter.generate(dimension_scores)
    
    return report
```

### 日志输出
```
[score_candidate] START Input: {"resume": {...}, "requirements": {...}}
[score_candidate] END Duration: 125.43ms Status: success Output: {"overall_score": 86, ...}
```

### Session 绑定

在 HRAgent 中,此工具通过闭包绑定到特定 session:

```python
def _make_tools(session_id: str) -> list:
    @traced_tool("score_candidate")
    @tool
    def score_candidate(resume: dict, requirements: dict) -> str:
        result = run_score_candidate(resume, requirements)
        _report_store[session_id] = result  # 存储到 session
        return json.dumps(result, ensure_ascii=False)
    
    return [parse_jd_tool, score_candidate, ...]
```

---

## 3. generate_report_html

### 功能
根据评分报告生成美观的 HTML 展示页面。

### 位置
`app/agent/tools/generate_report_html.py`

### 签名
```python
@traced_tool("generate_report_html")
@tool
def generate_report_html(report: dict) -> str:
    """生成 HTML 报告,返回状态消息"""
```

### 输入
- `report` (dict): 匹配报告对象 (序列化)

### 输出
```
"html_generated"  # 简单状态消息
```

**注意**: 真实的 HTML 内容存储在 `_html_store[session_id]` 中。

### 实现
```python
def run_generate_report_html(report: dict) -> str:
    """实际执行 HTML 生成"""
    # 1. 反序列化
    match_report = MatchReport(**report)
    
    # 2. 通过 MCP 工具搜索 UI 组件
    shadcn_results = search_shadcn_docs(
        query="dashboard report card component",
        count=3
    )
    
    # 3. 根据 shadcn 风格生成 HTML
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-gray-50">
        <div class="max-w-4xl mx-auto p-8">
            <!-- 评分卡片 -->
            <div class="bg-white rounded-lg shadow p-6">
                <h2>综合评分: {match_report.overall_score}</h2>
                <p>推荐结论: {match_report.recommendation}</p>
                <!-- 维度详情 -->
                ...
            </div>
        </div>
    </body>
    </html>
    """
    
    return html
```

### 日志输出
```
[generate_report_html] START Input: {"overall_score": 86, ...}
[generate_report_html] END Duration: 1876.23ms Status: success Output: "html_generated"
```

### Session 绑定

```python
def _make_tools(session_id: str) -> list:
    @traced_tool("generate_report_html")
    @tool
    def generate_report_html(report: dict) -> str:
        html = run_generate_report_html(report)
        _html_store[session_id] = html  # 存储到 session
        return "html_generated"
    
    return [parse_jd_tool, score_candidate, generate_report_html]
```

---

## 工具装饰器

### @traced_tool

记录工具执行的详细日志,包括输入、输出、耗时和状态。

```python
# app/utils/logger.py
def traced_tool(tool_name: str = None):
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            name = tool_name or func.__name__
            
            # 输入预览
            input_preview = _format_input(args, kwargs)
            logger.info(f"[{name}] START Input: {input_preview}")
            
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = (time.time() - start_time) * 1000
                output_preview = _format_output(result)
                logger.info(f"[{name}] END Duration: {duration:.2f}ms Status: success Output: {output_preview}")
                return result
            except Exception as e:
                duration = (time.time() - start_time) * 1000
                logger.error(f"[{name}] END Duration: {duration:.2f}ms Status: error Output: None Error: {e}")
                raise
        
        return wrapper
    return decorator
```

### 装饰器顺序

⚠️ **重要**: `@tool` 必须在 `@traced_tool` 之后应用

```python
# ✅ 正确
@traced_tool("my_tool")
@tool
def my_tool():
    pass

# ❌ 错误 (TypeError: 'StructuredTool' object is not callable)
@tool
@traced_tool("my_tool")
def my_tool():
    pass
```

**原因**: 
- `@tool` 将函数转换为 `StructuredTool` 对象 (LangChain)
- `@traced_tool` 需要包装原始的可调用函数
- 顺序错误会导致 `@traced_tool` 尝试包装一个不可调用的对象

---

## 工具调用流程

### 完整流程图

```
HRAgent.run(resume, jd_text)
    │
    ├─▶ 1. _make_tools(session_id)
    │      创建工具实例,绑定 session
    │
    ├─▶ 2. create_react_agent(model, tools)
    │      构建 LangGraph ReAct Agent
    │
    ├─▶ 3. graph.invoke(messages)
    │      ┌─────────────────────────────────┐
    │      │ LLM: "需要调用 parse_jd"         │
    │      └─────────────────────────────────┘
    │                 ↓
    │      ┌─────────────────────────────────┐
    │      │ Tool Executor:                  │
    │      │   parse_jd_tool(jd_text)        │
    │      │   [parse_jd] START...           │
    │      │   JDParser.parse()              │
    │      │   [parse_jd] END 2134.56ms      │
    │      └─────────────────────────────────┘
    │                 ↓
    │      ┌─────────────────────────────────┐
    │      │ LLM: "已获取需求,调用 score"     │
    │      └─────────────────────────────────┘
    │                 ↓
    │      ┌─────────────────────────────────┐
    │      │ Tool Executor:                  │
    │      │   score_candidate(resume, req)  │
    │      │   [score_candidate] START...    │
    │      │   Matcher + Reporter            │
    │      │   [score_candidate] END 125ms   │
    │      │   _report_store[sid] = result   │
    │      └─────────────────────────────────┘
    │                 ↓
    │      ┌─────────────────────────────────┐
    │      │ LLM: "已评分,生成 HTML"          │
    │      └─────────────────────────────────┘
    │                 ↓
    │      ┌─────────────────────────────────┐
    │      │ Tool Executor:                  │
    │      │   generate_report_html(report)  │
    │      │   [generate_html] START...      │
    │      │   UI/UX MCP 搜索 + 生成         │
    │      │   [generate_html] END 1876ms    │
    │      │   _html_store[sid] = html       │
    │      └─────────────────────────────────┘
    │                 ↓
    │      ┌─────────────────────────────────┐
    │      │ LLM: "评估完成,推荐该候选人"     │
    │      └─────────────────────────────────┘
    │
    └─▶ 4. 从 store 读取结果
           report = _report_store[session_id]
           html = _html_store[session_id]
```

---

## 日志示例

### 完整流程日志

```
2026-04-03 15:52:00,123 INFO [parse_jd] START Input: "招聘Python工程师，3年经验，本科学历..."
2026-04-03 15:52:02,257 INFO [parse_jd] END Duration: 2134.56ms Status: success Output: {"technical_skills": ["Python", "FastAPI"], "years_of_experience": 3, ...}

2026-04-03 15:52:03,334 INFO [score_candidate] START Input: {"resume": {"name": "张三", ...}, "requirements": {...}}
2026-04-03 15:52:03,460 INFO [score_candidate] END Duration: 125.43ms Status: success Output: {"overall_score": 86, "recommendation": "推荐", ...}

2026-04-03 15:52:04,521 INFO [generate_report_html] START Input: {"overall_score": 86, ...}
2026-04-03 15:52:06,397 INFO [generate_report_html] END Duration: 1876.23ms Status: success Output: "html_generated"
```

### 错误日志

```
2026-04-03 15:52:00,123 INFO [parse_jd] START Input: "招聘..."
2026-04-03 15:52:10,725 ERROR [parse_jd] END Duration: 10602.42ms Status: error Output: None Error: Failed to parse JD: Expecting value: line 1 column 1 (char 0)
```

---

## 性能统计

### 典型耗时

| 工具 | 平均耗时 | 瓶颈 |
|-----|---------|-----|
| `parse_jd` | 2-3秒 | LLM 推理 (MiniMax API) |
| `score_candidate` | 100-200ms | 纯本地计算,极快 |
| `generate_report_html` | 1-2秒 | UI/UX MCP 搜索 |

### 优化建议

#### 1. 缓存 JD 解析结果
```python
from functools import lru_cache

@lru_cache(maxsize=100)
def run_parse_jd(jd_text: str) -> dict:
    # 相同 JD 不重复解析
```

#### 2. 预加载 UI 模板
```python
# 避免每次搜索 shadcn
_HTML_TEMPLATE = load_template("report.html")

def run_generate_report_html(report: dict) -> str:
    return _HTML_TEMPLATE.format(**report)
```

---

## 测试

### 单元测试示例

```python
# tests/test_tools.py
from app.agent.tools.parse_jd import run_parse_jd
from app.agent.tools.score_candidate import run_score_candidate
from app.agent.tools.generate_report_html import run_generate_report_html

def test_parse_jd():
    jd_text = "招聘Python工程师，3年经验，本科学历"
    result = run_parse_jd(jd_text)
    
    assert "technical_skills" in result
    assert result["years_of_experience"] == 3
    assert result["education_required"] == "本科"

def test_score_candidate():
    resume = {"name": "张三", "skills": ["Python"], ...}
    requirements = {"technical_skills": ["Python"], ...}
    
    result = run_score_candidate(resume, requirements)
    
    assert "overall_score" in result
    assert 0 <= result["overall_score"] <= 100
    assert result["recommendation"] in ["推荐", "不推荐"]

def test_generate_report_html():
    report = {
        "overall_score": 86,
        "recommendation": "推荐",
        "dimensions": {...},
        "reasons": [...]
    }
    
    html = run_generate_report_html(report)
    
    assert "<html>" in html
    assert "86" in html
    assert "推荐" in html
```

---

## 常见问题 (FAQ)

### Q1: 为什么工具返回字符串而不是对象?

**A**: LangChain 的 `@tool` 装饰器要求工具返回可序列化的类型 (str, int, dict 等)。字符串是最通用的格式。

### Q2: 为什么 generate_report_html 返回 "html_generated" 而不是实际 HTML?

**A**: 
- LLM 不需要看到完整的 HTML 内容 (太长,浪费 tokens)
- 实际 HTML 通过 session store 传递给 HRAgent
- 这是一种"副作用"模式 (side effect)

### Q3: 如何添加新工具?

**A**: 
```python
# 1. 创建工具文件
# app/agent/tools/my_new_tool.py

from langchain_core.tools import tool
from app.utils.logger import traced_tool

@traced_tool("my_new_tool")
@tool
def my_new_tool(param: str) -> str:
    """工具描述,LLM 会看到这个"""
    result = do_something(param)
    return str(result)

# 2. 在 HRAgent 中注册
def _make_tools(session_id: str) -> list:
    return [
        parse_jd_tool,
        score_candidate,
        generate_report_html,
        my_new_tool  # 新工具
    ]
```

### Q4: 装饰器顺序记不住怎么办?

**A**: 记住口诀: **"追踪在前,工具在后"** (`@traced_tool` → `@tool`)

---

## 未来改进方向

### 1. 异步工具
```python
from langchain_core.tools import atool

@traced_tool("parse_jd")
@atool
async def parse_jd_async(jd_text: str) -> str:
    """异步版本"""
    result = await parser.parse_async(jd_text)
    return json.dumps(result)
```

### 2. 工具参数验证
```python
from pydantic import BaseModel

class ScoreCandidateInput(BaseModel):
    resume: dict
    requirements: dict

@traced_tool("score_candidate")
@tool(args_schema=ScoreCandidateInput)
def score_candidate(resume: dict, requirements: dict) -> str:
    # Pydantic 自动验证输入
    ...
```

### 3. 工具结果缓存
```python
from cachetools import TTLCache

_tool_cache = TTLCache(maxsize=100, ttl=300)  # 5分钟过期

@traced_tool("parse_jd")
@tool
def parse_jd(jd_text: str) -> str:
    cache_key = hash(jd_text)
    if cache_key in _tool_cache:
        return _tool_cache[cache_key]
    
    result = run_parse_jd(jd_text)
    _tool_cache[cache_key] = result
    return result
```

---

## 维护历史

| 日期 | 版本 | 变更说明 |
|------|------|---------|
| 2026-04-03 | 1.0.0 | 初始版本,三个核心工具 + 追踪日志 |
