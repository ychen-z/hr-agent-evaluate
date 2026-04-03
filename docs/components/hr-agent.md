# HRAgent 组件文档

## 概述

`HRAgent` 是 HR Agent 系统的核心调度组件,基于 LangGraph 的 ReAct Agent 模式,负责编排整个简历评估流程。它通过 LLM 智能决策,按顺序调用三个工具完成评估任务。

## 核心功能

### 功能定位
**AI Agent 调度器** - 智能编排评估流程

```
用户请求 → HRAgent → 工具编排 → 结果返回
              ↓
         ┌─────────────┐
         │ LLM 决策    │
         │ ReAct 循环  │
         └─────────────┘
              ↓
    parse_jd → score → generate_html
```

## 在系统中的位置

```
┌──────────────────────────────────────────┐
│            HRAgent (核心编排器)            │
├──────────────────────────────────────────┤
│                                          │
│  输入: Resume + JD Text                  │
│         ↓                                │
│  ┌────────────────────────────────────┐ │
│  │ LangGraph ReAct Agent              │ │
│  │                                    │ │
│  │  LLM (MiniMax-M2.5)               │ │
│  │    ↓                              │ │
│  │  Tool 1: parse_jd                 │ │
│  │    ↓                              │ │
│  │  Tool 2: score_candidate          │ │
│  │    ↓                              │ │
│  │  Tool 3: generate_report_html     │ │
│  │    ↓                              │ │
│  │  生成总结推理                       │ │
│  └────────────────────────────────────┘ │
│         ↓                                │
│  输出: AgentResult                       │
│    - session_id                         │
│    - report (MatchReport)               │
│    - html                               │
│    - reasoning                          │
│                                          │
└──────────────────────────────────────────┘
```

## 数据模型

### 输入
```python
resume: Resume           # 候选人简历对象
jd_text: str            # 职位描述文本
```

### 输出
```python
class AgentResult(BaseModel):
    session_id: str        # 会话唯一标识
    report: MatchReport    # 评估报告
    html: str             # HTML 报告页面
    reasoning: str        # Agent 的推理总结
```

## 工作原理

### ReAct 循环

```
HRAgent.run(resume, jd_text)
    │
    ├─▶ 1. 生成 session_id (UUID)
    │
    ├─▶ 2. 构建工具列表
    │      _make_tools(session_id)
    │      • parse_jd_tool (全局)
    │      • score_candidate (闭包,绑定 session_id)
    │      • generate_report_html (闭包,绑定 session_id)
    │
    ├─▶ 3. 创建 ReAct Agent
    │      create_react_agent(model, tool_node)
    │
    ├─▶ 4. 构建提示消息
    │      SystemMessage: 角色定义 + 工具调用顺序
    │      HumanMessage: 具体任务 + JD + 简历
    │
    ├─▶ 5. Agent 执行循环
    │      graph.invoke(messages)
    │      ┌──────────────────────────┐
    │      │ LLM 推理 → 决定调用工具   │
    │      │   ↓                      │
    │      │ 调用 parse_jd            │
    │      │   ↓                      │
    │      │ 观察结果 → 继续推理       │
    │      │   ↓                      │
    │      │ 调用 score_candidate     │
    │      │   ↓                      │
    │      │ 观察结果 → 继续推理       │
    │      │   ↓                      │
    │      │ 调用 generate_report_html│
    │      │   ↓                      │
    │      │ 生成总结                 │
    │      └──────────────────────────┘
    │
    ├─▶ 6. 提取推理总结
    │      从 AIMessage 中提取最后的推理内容
    │
    ├─▶ 7. 从 store 获取结果
    │      report_dict = _report_store[session_id]
    │      html = _html_store[session_id]
    │
    └─▶ 8. 返回 AgentResult
```

### System Prompt

```python
_SYSTEM_PROMPT = """你是一位专业的HR评估专家。你需要对候选人进行全面评估，并严格按以下顺序调用工具：

1. 调用 parse_jd 解析职位描述，获取结构化需求
2. 调用 score_candidate，传入候选人简历和第一步返回的需求，计算匹配分数
3. 调用 generate_report_html，传入第二步返回的评分报告，生成HTML报告

完成三步后，输出一段中文总结，说明评估结论和推荐理由。不要跳过任何步骤。"""
```

### 工具绑定机制

```python
def _make_tools(session_id: str) -> list:
    """通过闭包将 session_id 绑定到工具"""
    
    @tool
    def score_candidate(resume: dict, requirements: dict) -> str:
        result = run_score_candidate(resume, requirements)
        _report_store[session_id] = result  # 存储到 session store
        return json.dumps(result, ensure_ascii=False)
    
    @tool
    def generate_report_html(report: dict) -> str:
        html = run_generate_report_html(report)
        _html_store[session_id] = html  # 存储到 session store
        return "html_generated"
    
    return [parse_jd_tool, score_candidate, generate_report_html]
```

## 使用示例

### 基本使用

```python
from app.agent.hr_agent import HRAgent
from app.types.models import Resume, Education, Experience

# 创建 Agent
agent = HRAgent()

# 准备简历
resume = Resume(
    name="张三",
    email="zhangsan@example.com",
    phone="138****0000",
    education=[Education(degree="本科", major="计算机", school="清华", year=2018)],
    experience=[Experience(company="字节", position="Python工程师", duration="3年", description="后端")],
    skills=["Python", "FastAPI"],
    soft_skills=["沟通能力"]
)

# JD 文本
jd_text = "招聘Python工程师，3年经验，熟悉FastAPI"

# 执行评估
try:
    result = agent.run(resume, jd_text)
    
    print(f"Session ID: {result.session_id}")
    print(f"Overall Score: {result.report.overall_score}")
    print(f"Recommendation: {result.report.recommendation}")
    print(f"Reasoning: {result.reasoning}")
    print(f"HTML Length: {len(result.html)} chars")
    
except AgentLoopError as e:
    print(f"Agent error: {e}")
```

### 在 API 中使用

```python
# app/api/routes.py
@router.post("/api/v1/agent/match")
async def agent_match_resume(request: MatchRequest):
    try:
        agent = HRAgent()
        result = agent.run(request.resume, request.job_description)
        return result
    except AgentLoopError as e:
        raise HTTPException(status_code=503, detail=str(e))
```

## 状态管理

### Session Store

```python
# 模块级别的字典存储
_html_store: dict[str, str] = {}       # session_id → HTML
_report_store: dict[str, dict] = {}    # session_id → report dict

# 存储 (在工具中)
_report_store[session_id] = result

# 读取 (在 Agent 中)
report_dict = _report_store.get(session_id, {})
html = _html_store.get(session_id, "")
```

**注意事项**:
- ✅ 在单进程 uvicorn 下线程安全 (CPython GIL)
- ❌ 在多进程模式下不安全 (`uvicorn --workers N`)
- ⚠️ 没有自动清理机制,长期运行会积累内存

**生产环境建议**:
```python
# 使用 LRU 缓存
from cachetools import LRUCache
_html_store = LRUCache(maxsize=1000)

# 或使用 Redis
import redis
redis_client = redis.Redis()
```

## 错误处理

### AgentLoopError

```python
class AgentLoopError(Exception):
    """Agent 循环异常"""
    pass

# 触发场景:
# 1. 超过最大迭代次数
raise AgentLoopError("Agent exceeded maximum iterations")

# 2. 工具未产生预期输出
raise AgentLoopError("Agent did not produce a score report")
raise AgentLoopError("Agent did not produce an HTML report")
```

### 异常捕获

```python
try:
    result = graph.invoke(...)
except GraphRecursionError as e:
    raise AgentLoopError("Agent exceeded maximum iterations") from e
```

## 性能考虑

### 典型执行时间

```
完整流程耗时:
├─ LLM 推理 1: ~1s    (决定调用 parse_jd)
├─ parse_jd: ~2s      (LLM 解析 JD)
├─ LLM 推理 2: ~1s    (决定调用 score_candidate)
├─ score_candidate: ~0.1s (本地计算)
├─ LLM 推理 3: ~1s    (决定调用 generate_html)
├─ generate_html: ~2s (UI-UX 搜索)
└─ LLM 总结: ~1s      (生成推理)
─────────────────────
总计: ~8-10秒
```

### 优化建议

#### 1. 减少 LLM 调用次数
```python
# 当前: LLM 推理 4 次
# 优化: 使用计划模式,一次性生成完整计划

# 或使用函数调用 (Function Calling)
# LLM 一次返回所有工具调用
```

#### 2. 并行无依赖工具
```python
# 当前是强依赖链,无法并行
# 如果有独立工具可并行:
import asyncio
results = await asyncio.gather(
    tool1.ainvoke(...),
    tool2.ainvoke(...)
)
```

## 测试

### 单元测试示例

```python
# tests/test_hr_agent.py
from unittest.mock import MagicMock, patch
from app.agent.hr_agent import HRAgent, AgentLoopError

def test_agent_run_returns_agent_result():
    fake_graph = MagicMock()
    
    def fake_invoke(messages, config):
        sid = config["configurable"]["thread_id"]
        _report_store[sid] = {"overall_score": 85}
        _html_store[sid] = "<html>report</html>"
        return {"messages": [AIMessage(content="推荐该候选人")]}
    
    fake_graph.invoke.side_effect = fake_invoke
    
    with patch("app.agent.hr_agent.create_react_agent", return_value=fake_graph):
        agent = HRAgent()
        result = agent.run(resume, jd_text)
        
        assert result.session_id
        assert result.report.overall_score == 85
        assert result.html == "<html>report</html>"
        assert result.reasoning == "推荐该候选人"
```

## 常见问题 (FAQ)

### Q1: 为什么使用 ReAct 而不是简单的顺序调用?

**A**: 
- ReAct 提供灵活性,LLM 可以根据中间结果调整策略
- 支持错误重试和异常处理
- 可扩展性强,易于添加新工具

### Q2: Session Store 什么时候清理?

**A**: 当前版本没有自动清理。建议:
```python
# 定时清理
from apscheduler.schedulers.background import BackgroundScheduler

def cleanup_old_sessions():
    # 清理 1 小时前的 session
    pass

scheduler = BackgroundScheduler()
scheduler.add_job(cleanup_old_sessions, 'interval', hours=1)
```

### Q3: 如何限制 Agent 的最大迭代次数?

**A**: LangGraph 有内置限制,可通过配置调整:
```python
graph.invoke(
    messages,
    config={
        "configurable": {"thread_id": session_id},
        "recursion_limit": 20  # 默认 25
    }
)
```

## 未来改进方向

### 1. 流式输出
```python
async def run_streaming(self, resume, jd_text):
    async for event in graph.astream_events(...):
        yield event  # 实时返回 Agent 状态
```

### 2. 工具并行执行
```python
# 支持声明独立工具
independent_tools = ["get_weather", "get_salary_benchmark"]
# LLM 可同时调用
```

### 3. 多 Agent 协作
```python
class TeamAgent:
    def __init__(self):
        self.parser_agent = ParserAgent()
        self.scorer_agent = ScorerAgent()
        # 专业化分工
```

## 维护历史

| 日期 | 版本 | 变更说明 |
|------|------|---------|
| 2026-04-03 | 1.0.0 | 基于 LangGraph ReAct 的初始版本 |
