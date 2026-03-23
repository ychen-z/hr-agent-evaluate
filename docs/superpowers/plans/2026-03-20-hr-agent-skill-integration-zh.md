# HR Agent 技能集成实施计划

> **针对 AI 工作者：** 必须使用 superpowers:subagent-driven-development（如果有子代理可用）或 superpowers:executing-plans 来实施此计划。步骤使用复选框（`- [ ]`）语法进行跟踪。

**目标：** 引入 `HRAgent`，通过 Claude 的 `tool_use` 循环暴露三个技能（`parse_jd`、`score_candidate`、`generate_report_html`），以及两个新的 API 端点，且不修改现有代码。

**架构：** `HRAgent` 驱动一个 Claude tool_use 循环；每个技能都是对现有流水线代码或新 HTML 生成器的轻量级适配器。在 `hr_agent.py` 中有一个模块级别的 `_html_store` 字典，将 `session_id` 映射到生成的 HTML，通过 GET 端点检索。

**技术栈：** Python 3.10+、FastAPI、Pydantic v2、Anthropic SDK >= 0.18.0、subprocess（用于 ui-ux-pro-max 搜索脚本）、pytest

---

## 模块 1：数据模型 + AgentLoopError

### 任务 1：添加 `AgentResult` 模型和 `AgentLoopError`

**文件：**

- 修改：`app/types/models.py`
- 修改：`app/agent/__init__.py`（创建）
- 修改：`app/agent/hr_agent.py`（创建 — 目前只包含异常）
- 测试：`tests/test_models.py`（创建）

- [ ] **步骤 1：编写失败的测试**

```python
# tests/test_models.py
from app.types.models import AgentResult, MatchReport

def test_agent_result_model():
    report = MatchReport(
        overall_score=85,
        dimensions={},
        recommendation="推荐",
        reasons=["技术栈匹配度高"]
    )
    result = AgentResult(
        session_id="abc-123",
        report=report,
        html="<html></html>",
        reasoning="候选人综合评估良好"
    )
    assert result.session_id == "abc-123"
    assert result.report.overall_score == 85
    assert result.html == "<html></html>"
    assert result.reasoning == "候选人综合评估良好"
```

- [ ] **步骤 2：运行测试验证其失败**

```bash
pytest tests/test_models.py::test_agent_result_model -v
```

预期结果：失败，报 `ImportError: cannot import name 'AgentResult'`

- [ ] **步骤 3：将 `AgentResult` 添加到 models**

在 `app/types/models.py` 中追加：

```python
class AgentResult(BaseModel):
    session_id: str
    report: MatchReport
    html: str
    reasoning: str
```

- [ ] **步骤 4：运行测试验证其通过**

```bash
pytest tests/test_models.py::test_agent_result_model -v
```

预期结果：通过

- [ ] **步骤 5：创建 `app/agent/__init__.py`（空包标记文件）**

创建该文件，不包含任何内容 — 它仅用于使 `app/agent` 成为一个 Python 包。

- [ ] **步骤 6：创建 `app/agent/hr_agent.py`，仅包含 `AgentLoopError`**

```python
class AgentLoopError(Exception):
    """当代理 tool_use 循环超过最大迭代次数时抛出。"""
```

- [ ] **步骤 7：为 `AgentLoopError` 编写测试**

在 `tests/test_models.py` 中追加：

```python
from app.agent.hr_agent import AgentLoopError

def test_agent_loop_error_is_exception():
    err = AgentLoopError("too many iterations")
    assert isinstance(err, Exception)
    assert str(err) == "too many iterations"
```

- [ ] **步骤 8：运行测试验证其通过**

```bash
pytest tests/test_models.py -v
```

预期结果：两个测试都通过

- [ ] **步骤 9：提交**

```bash
git add app/types/models.py app/agent/__init__.py app/agent/hr_agent.py tests/test_models.py
git commit -m "feat: add AgentResult model and AgentLoopError"
```

---

## 模块 2：工具适配器

### 任务 2：`parse_jd` 工具适配器

**文件：**

- 创建：`app/agent/tools/__init__.py`
- 创建：`app/agent/tools/parse_jd.py`
- 测试：`tests/test_agent_tools.py`（创建）

- [ ] **步骤 1：编写失败的测试**

```python
# tests/test_agent_tools.py
from unittest.mock import patch, MagicMock
from app.agent.tools.parse_jd import run_parse_jd

def test_parse_jd_returns_requirements_dict():
    mock_req = MagicMock()
    mock_req.model_dump.return_value = {
        "required_skills": ["Python"],
        "experience_years": 3,
        "education_level": "本科",
        "soft_skills": ["沟通能力"]
    }
    with patch("app.agent.tools.parse_jd.JDParser") as MockParser:
        MockParser.return_value.parse.return_value = mock_req
        result = run_parse_jd({"jd_text": "需要Python工程师，3年经验，本科"})
    assert result["required_skills"] == ["Python"]
    assert result["experience_years"] == 3

def test_parse_jd_returns_error_dict_on_exception():
    with patch("app.agent.tools.parse_jd.JDParser") as MockParser:
        MockParser.return_value.parse.side_effect = Exception("LLM unavailable")
        result = run_parse_jd({"jd_text": "some jd"})
    assert "error" in result
    assert "LLM unavailable" in result["error"]
```

- [ ] **步骤 2：运行测试验证其失败**

```bash
pytest tests/test_agent_tools.py::test_parse_jd_returns_requirements_dict -v
```

预期结果：失败，报 `ModuleNotFoundError`

- [ ] **步骤 3：创建 `app/agent/tools/__init__.py`（空包标记文件）**

- [ ] **步骤 4：实现 `app/agent/tools/parse_jd.py`**

```python
from app.pipeline.jd_parser import JDParser

def run_parse_jd(tool_input: dict) -> dict:
    """工具适配器：将原始 JD 文本解析为结构化的 JDRequirements 字典。"""
    try:
        jd_text = tool_input["jd_text"]
        parser = JDParser()
        requirements = parser.parse(jd_text)
        return requirements.model_dump()
    except Exception as e:
        return {"error": str(e)}

TOOL_SCHEMA = {
    "name": "parse_jd",
    "description": "解析职位描述文本，提取结构化需求（技能、经验年限、学历、软技能）",
    "input_schema": {
        "type": "object",
        "properties": {
            "jd_text": {
                "type": "string",
                "description": "原始职位描述文本"
            }
        },
        "required": ["jd_text"]
    }
}
```

- [ ] **步骤 5：运行测试验证其通过**

```bash
pytest tests/test_agent_tools.py::test_parse_jd_returns_requirements_dict tests/test_agent_tools.py::test_parse_jd_returns_error_dict_on_exception -v
```

预期结果：两个测试都通过

- [ ] **步骤 6：提交**

```bash
git add app/agent/tools/__init__.py app/agent/tools/parse_jd.py tests/test_agent_tools.py
git commit -m "feat: add parse_jd tool adapter"
```

---

### 任务 3：`score_candidate` 工具适配器

**文件：**

- 创建：`app/agent/tools/score_candidate.py`
- 测试：`tests/test_agent_tools.py`（追加）

- [ ] **步骤 1：编写失败的测试**

在 `tests/test_agent_tools.py` 中追加：

```python
from app.agent.tools.score_candidate import run_score_candidate

def test_score_candidate_returns_report_dict():
    tool_input = {
        "resume": {
            "name": "张三",
            "email": "z@example.com",
            "phone": "138",
            "education": [{"degree": "本科", "major": "计算机", "school": "某大学", "year": 2018}],
            "experience": [{"company": "A公司", "position": "工程师", "duration": "3年", "description": "Python开发"}],
            "skills": ["Python"],
            "soft_skills": ["沟通能力"]
        },
        "requirements": {
            "required_skills": ["Python"],
            "experience_years": 3,
            "education_level": "本科",
            "soft_skills": ["沟通能力"]
        }
    }
    result = run_score_candidate(tool_input)
    assert "overall_score" in result
    assert "recommendation" in result
    assert isinstance(result["overall_score"], int)

def test_score_candidate_returns_error_on_invalid_input():
    result = run_score_candidate({"resume": {}, "requirements": {}})
    assert "error" in result
```

- [ ] **步骤 2：运行测试验证其失败**

```bash
pytest tests/test_agent_tools.py::test_score_candidate_returns_report_dict -v
```

预期结果：失败，报 `ModuleNotFoundError`

- [ ] **步骤 3：实现 `app/agent/tools/score_candidate.py`**

```python
from pydantic import ValidationError
from app.types.models import Resume, JDRequirements
from app.pipeline.matcher import Matcher
from app.pipeline.reporter import Reporter

def run_score_candidate(tool_input: dict) -> dict:
    """工具适配器：根据解析后的 JD 需求对候选人简历进行评分。"""
    try:
        resume = Resume(**tool_input["resume"])
        requirements = JDRequirements(**tool_input["requirements"])
    except (ValidationError, KeyError) as e:
        return {"error": str(e)}

    try:
        matcher = Matcher()
        reporter = Reporter()
        dimension_scores = matcher.match(resume, requirements)
        report = reporter.generate(dimension_scores)
        if hasattr(report, "model_dump"):
            return report.model_dump()
        return report
    except Exception as e:
        return {"error": str(e)}

TOOL_SCHEMA = {
    "name": "score_candidate",
    "description": "根据解析后的职位需求对候选人简历进行评分，返回各维度分数和综合推荐结论",
    "input_schema": {
        "type": "object",
        "properties": {
            "resume": {
                "type": "object",
                "description": "候选人简历（Resume 结构体）"
            },
            "requirements": {
                "type": "object",
                "description": "由 parse_jd 返回的职位需求结构体"
            }
        },
        "required": ["resume", "requirements"]
    }
}
```

- [ ] **步骤 4：运行测试验证其通过**

```bash
pytest tests/test_agent_tools.py::test_score_candidate_returns_report_dict tests/test_agent_tools.py::test_score_candidate_returns_error_on_invalid_input -v
```

预期结果：两个测试都通过

- [ ] **步骤 5：提交**

```bash
git add app/agent/tools/score_candidate.py tests/test_agent_tools.py
git commit -m "feat: add score_candidate tool adapter"
```

---

### 任务 4：`generate_report_html` 工具

**文件：**

- 创建：`app/agent/tools/generate_report_html.py`
- 测试：`tests/test_agent_tools.py`（追加）

- [ ] **步骤 1：编写失败的测试**

在 `tests/test_agent_tools.py` 中追加：

```python
from unittest.mock import patch, MagicMock
from app.agent.tools.generate_report_html import run_generate_report_html

SAMPLE_REPORT = {
    "overall_score": 87,
    "dimensions": {
        "hard_skills": {"score": 90, "matched": ["Python"], "missing": [], "detail": None},
        "experience": {"score": 100, "matched": [], "missing": [], "detail": None},
        "education": {"score": 100, "matched": [], "missing": [], "detail": None},
        "soft_skills": {"score": 80, "matched": ["沟通能力"], "missing": [], "detail": None},
    },
    "recommendation": "推荐",
    "reasons": ["技术栈匹配度高", "工作经验符合要求"]
}

def test_generate_report_html_returns_html_string():
    with patch("app.agent.tools.generate_report_html.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="[]")
        result = run_generate_report_html({"report": SAMPLE_REPORT})
    assert isinstance(result, str)
    assert "<html" in result.lower()
    assert "87" in result

def test_generate_report_html_falls_back_when_scripts_unavailable():
    with patch("app.agent.tools.generate_report_html.subprocess.run") as mock_run:
        mock_run.side_effect = FileNotFoundError("script not found")
        result = run_generate_report_html({"report": SAMPLE_REPORT})
    assert isinstance(result, str)
    assert "<html" in result.lower()
    assert "87" in result
```

- [ ] **步骤 2：运行测试验证其失败**

```bash
pytest tests/test_agent_tools.py::test_generate_report_html_returns_html_string -v
```

预期结果：失败，报 `ModuleNotFoundError`

- [ ] **步骤 3：实现 `app/agent/tools/generate_report_html.py`**

（代码实现见英文版文档，包含完整的 HTML 模板生成逻辑）

- [ ] **步骤 4：运行测试验证其通过**

```bash
pytest tests/test_agent_tools.py::test_generate_report_html_returns_html_string tests/test_agent_tools.py::test_generate_report_html_falls_back_when_scripts_unavailable -v
```

预期结果：两个测试都通过

- [ ] **步骤 5：一起运行所有工具测试**

```bash
pytest tests/test_agent_tools.py -v
```

预期结果：全部通过

- [ ] **步骤 6：提交**

```bash
git add app/agent/tools/generate_report_html.py tests/test_agent_tools.py
git commit -m "feat: add generate_report_html tool with ui-ux-pro-max integration"
```

---

## 模块 3：HRAgent 循环

### 任务 5：`HRAgent` 类

**文件：**

- 修改：`app/agent/hr_agent.py`（完整实现）
- 测试：`tests/test_hr_agent.py`（创建）

- [ ] **步骤 1：编写失败的测试**

```python
# tests/test_hr_agent.py
import uuid
from unittest.mock import MagicMock, patch
from app.agent.hr_agent import HRAgent, AgentLoopError, _html_store

RESUME_DICT = {
    "name": "张三",
    "email": "z@example.com",
    "phone": "138",
    "education": [{"degree": "本科", "major": "计算机", "school": "某大学", "year": 2018}],
    "experience": [{"company": "A公司", "position": "工程师", "duration": "3年", "description": "Python开发"}],
    "skills": ["Python"],
    "soft_skills": ["沟通能力"]
}
JD_TEXT = "招募Python工程师，3年经验，本科学历"


def _make_tool_use_response(tool_name, tool_input, tool_use_id="tu_001"):
    block = MagicMock()
    block.type = "tool_use"
    block.name = tool_name
    block.input = tool_input
    block.id = tool_use_id
    response = MagicMock()
    response.stop_reason = "tool_use"
    response.content = [block]
    return response


def _make_end_turn_response(text="评估完成，推荐该候选人"):
    block = MagicMock()
    block.type = "text"
    block.text = text
    response = MagicMock()
    response.stop_reason = "end_turn"
    response.content = [block]
    return response


def test_agent_run_completes_full_loop():
    """代理调用所有三个工具并返回 AgentResult。"""
    from app.types.models import Resume

    resume = Resume(**RESUME_DICT)
    requirements_dict = {"required_skills": ["Python"], "experience_years": 3, "education_level": "本科", "soft_skills": ["沟通能力"]}
    report_dict = {"overall_score": 87, "dimensions": {}, "recommendation": "推荐", "reasons": ["技术栈匹配度高"]}

    with patch("app.agent.hr_agent.Anthropic") as MockAnthropic, \
         patch("app.agent.hr_agent.run_parse_jd", return_value=requirements_dict), \
         patch("app.agent.hr_agent.run_score_candidate", return_value=report_dict), \
         patch("app.agent.hr_agent.run_generate_report_html", return_value="<html>report</html>"):

        mock_client = MockAnthropic.return_value
        mock_client.messages.create.side_effect = [
            _make_tool_use_response("parse_jd", {"jd_text": JD_TEXT}),
            _make_tool_use_response("score_candidate", {"resume": RESUME_DICT, "requirements": requirements_dict}, "tu_002"),
            _make_tool_use_response("generate_report_html", {"report": report_dict}, "tu_003"),
            _make_end_turn_response("推荐该候选人"),
        ]

        agent = HRAgent()
        result = agent.run(resume, JD_TEXT)

    assert result.report.overall_score == 87
    assert result.html == "<html>report</html>"
    assert "推荐" in result.reasoning
    assert result.session_id in _html_store


def test_agent_raises_on_loop_limit():
    """当循环超过最大迭代次数时，代理抛出 AgentLoopError。"""
    from app.types.models import Resume

    resume = Resume(**RESUME_DICT)

    with patch("app.agent.hr_agent.Anthropic") as MockAnthropic, \
         patch("app.agent.hr_agent.run_parse_jd", return_value={}):

        mock_client = MockAnthropic.return_value
        mock_client.messages.create.return_value = _make_tool_use_response(
            "parse_jd", {"jd_text": JD_TEXT}
        )

        agent = HRAgent(max_iterations=3)
        try:
            agent.run(resume, JD_TEXT)
            assert False, "Should have raised AgentLoopError"
        except AgentLoopError:
            pass
```

- [ ] **步骤 2：运行测试验证其失败**

```bash
pytest tests/test_hr_agent.py::test_agent_run_completes_full_loop -v
```

预期结果：失败，报 `ImportError`

- [ ] **步骤 3：实现 `app/agent/hr_agent.py`（完整版）**

（完整实现代码见英文版文档）

- [ ] **步骤 4：运行测试验证其通过**

```bash
pytest tests/test_hr_agent.py -v
```

预期结果：两个测试都通过

- [ ] **步骤 5：运行所有测试以确认没有回归**

```bash
pytest -v
```

预期结果：全部通过

- [ ] **步骤 6：提交**

```bash
git add app/agent/hr_agent.py tests/test_hr_agent.py
git commit -m "feat: implement HRAgent tool_use loop"
```

---

## 模块 4：API 端点

### 任务 6：新 API 端点

**文件：**

- 修改：`app/api/routes.py`
- 测试：`tests/test_api.py`（追加）

- [ ] **步骤 1：编写失败的测试**

在 `tests/test_api.py` 中追加：

```python
from app.agent.hr_agent import _html_store

AGENT_REQUEST = {
    "resume": {
        "name": "张三",
        "email": "z@example.com",
        "phone": "138",
        "education": [{"degree": "本科", "major": "计算机", "school": "某大学", "year": 2018}],
        "experience": [{"company": "A公司", "position": "工程师", "duration": "3年", "description": "Python开发"}],
        "skills": ["Python"],
        "soft_skills": ["沟通能力"]
    },
    "job_description": "招募Python工程师，3年经验，本科学历"
}


def test_agent_match_endpoint_returns_agent_result():
    from unittest.mock import patch
    from app.types.models import AgentResult, MatchReport

    mock_report = MatchReport(
        overall_score=87,
        dimensions={},
        recommendation="推荐",
        reasons=["技术栈匹配度高"]
    )
    mock_result = AgentResult(
        session_id="test-session-001",
        report=mock_report,
        html="<html>report</html>",
        reasoning="推荐该候选人"
    )

    with patch("app.api.routes.HRAgent") as MockAgent:
        MockAgent.return_value.run.return_value = mock_result
        response = client.post(
            "/api/v1/agent/match",
            json=AGENT_REQUEST,
            headers={"X-API-Key": "test-key"}
        )

    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == "test-session-001"
    assert data["report"]["overall_score"] == 87
    assert data["html"] == "<html>report</html>"


def test_agent_report_endpoint_returns_html():
    _html_store["test-session-002"] = "<html><body>report</body></html>"
    response = client.get("/api/v1/agent/report/test-session-002")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "<html>" in response.text


def test_agent_report_endpoint_returns_404_for_unknown_session():
    response = client.get("/api/v1/agent/report/nonexistent-session")
    assert response.status_code == 404
```

- [ ] **步骤 2：运行测试验证其失败**

```bash
pytest tests/test_api.py::test_agent_match_endpoint_returns_agent_result -v
```

预期结果：失败（端点尚未添加）

- [ ] **步骤 3：将新端点添加到 `app/api/routes.py`**

在 `app/api/routes.py` 末尾追加：

```python
from fastapi.responses import HTMLResponse
from app.agent.hr_agent import HRAgent, AgentLoopError, _html_store
from app.types.models import AgentResult

@router.post("/api/v1/agent/match", response_model=AgentResult)
async def agent_match_resume(
    request: MatchRequest,
    x_api_key: str = Header(None, alias="X-API-Key")
):
    api_key = os.getenv("API_KEY")
    if api_key and x_api_key != api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")

    if not request.job_description or len(request.job_description.strip()) < 5:
        raise HTTPException(status_code=400, detail="Job description too short")

    try:
        agent = HRAgent()
        result = agent.run(request.resume, request.job_description)
        return result
    except AgentLoopError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception:
        raise HTTPException(status_code=503, detail="Service temporarily unavailable")


@router.get("/api/v1/agent/report/{session_id}", response_class=HTMLResponse)
async def get_agent_report(session_id: str):
    html = _html_store.get(session_id)
    if html is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return HTMLResponse(content=html)
```

- [ ] **步骤 4：运行新端点测试**

```bash
pytest tests/test_api.py::test_agent_match_endpoint_returns_agent_result tests/test_api.py::test_agent_report_endpoint_returns_html tests/test_api.py::test_agent_report_endpoint_returns_404_for_unknown_session -v
```

预期结果：全部通过

- [ ] **步骤 5：运行完整测试套件**

```bash
pytest -v
```

预期结果：全部通过，现有测试无回归

- [ ] **步骤 6：提交**

```bash
git add app/api/routes.py tests/test_api.py
git commit -m "feat: add /api/v1/agent/match and /api/v1/agent/report endpoints"
```

---

## 模块 5：最终验证

### 任务 7：端到端冒烟测试 + 清理

**文件：**

- 无新文件

- [ ] **步骤 1：最后运行一次完整测试套件**

```bash
pytest -v --tb=short
```

预期结果：所有测试通过

- [ ] **步骤 2：验证服务器启动无错误**

```bash
uvicorn app.main:app --reload &
sleep 2
curl -s http://localhost:8000/health
kill %1
```

预期输出：`{"status":"ok"}`

- [ ] **步骤 3：最终提交**

```bash
git status
git add app/ tests/
git commit -m "feat: HR Agent skill integration complete"
```
