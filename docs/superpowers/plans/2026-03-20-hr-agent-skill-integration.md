# HR Agent Skill Integration Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Introduce `HRAgent` with a Claude `tool_use` loop exposing three skills (`parse_jd`, `score_candidate`, `generate_report_html`), plus two new API endpoints, without touching existing code.

**Architecture:** `HRAgent` drives a Claude tool_use loop; each skill is a thin adapter over existing pipeline code or a new HTML generator. A module-level `_html_store` dict in `hr_agent.py` maps `session_id` to generated HTML, retrieved by the GET endpoint.

**Tech Stack:** Python 3.10+, FastAPI, Pydantic v2, Anthropic SDK >= 0.18.0, subprocess (for ui-ux-pro-max search scripts), pytest

---

## Chunk 1: Data Models + AgentLoopError

### Task 1: Add `AgentResult` model and `AgentLoopError`

**Files:**
- Modify: `app/types/models.py`
- Modify: `app/agent/__init__.py` (create)
- Modify: `app/agent/hr_agent.py` (create — exception only for now)
- Test: `tests/test_models.py` (create)

- [ ] **Step 1: Write the failing test**

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

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_models.py::test_agent_result_model -v
```

Expected: FAIL with `ImportError: cannot import name 'AgentResult'`

- [ ] **Step 3: Add `AgentResult` to models**

In `app/types/models.py`, append:

```python
class AgentResult(BaseModel):
    session_id: str
    report: MatchReport
    html: str
    reasoning: str
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_models.py::test_agent_result_model -v
```

Expected: PASS

- [ ] **Step 5: Create `app/agent/__init__.py` (empty package marker)**

Create the file with no contents — it exists only to make `app/agent` a Python package.

- [ ] **Step 6: Create `app/agent/hr_agent.py` with `AgentLoopError` only**

```python
class AgentLoopError(Exception):
    """Raised when the agent tool_use loop exceeds the maximum iteration limit."""
```

- [ ] **Step 7: Write test for `AgentLoopError`**

In `tests/test_models.py`, append:

```python
from app.agent.hr_agent import AgentLoopError

def test_agent_loop_error_is_exception():
    err = AgentLoopError("too many iterations")
    assert isinstance(err, Exception)
    assert str(err) == "too many iterations"
```

- [ ] **Step 8: Run test to verify it passes**

```bash
pytest tests/test_models.py -v
```

Expected: both tests PASS

- [ ] **Step 9: Commit**

```bash
git add app/types/models.py app/agent/__init__.py app/agent/hr_agent.py tests/test_models.py
git commit -m "feat: add AgentResult model and AgentLoopError"
```

---

## Chunk 2: Tool Adapters

### Task 2: `parse_jd` tool adapter

**Files:**
- Create: `app/agent/tools/__init__.py`
- Create: `app/agent/tools/parse_jd.py`
- Test: `tests/test_agent_tools.py` (create)

- [ ] **Step 1: Write the failing test**

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

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_agent_tools.py::test_parse_jd_returns_requirements_dict -v
```

Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Create `app/agent/tools/__init__.py` (empty package marker)**

Create the file with no contents — it exists only to make `app/agent/tools` a Python package.

- [ ] **Step 4: Implement `app/agent/tools/parse_jd.py`**

```python
from app.pipeline.jd_parser import JDParser

def run_parse_jd(tool_input: dict) -> dict:
    """Tool adapter: parse raw JD text into structured JDRequirements dict."""
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

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/test_agent_tools.py::test_parse_jd_returns_requirements_dict tests/test_agent_tools.py::test_parse_jd_returns_error_dict_on_exception -v
```

Expected: both PASS

- [ ] **Step 6: Commit**

```bash
git add app/agent/tools/__init__.py app/agent/tools/parse_jd.py tests/test_agent_tools.py
git commit -m "feat: add parse_jd tool adapter"
```

---

### Task 3: `score_candidate` tool adapter

**Files:**
- Create: `app/agent/tools/score_candidate.py`
- Test: `tests/test_agent_tools.py` (append)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_agent_tools.py`:

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

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_agent_tools.py::test_score_candidate_returns_report_dict -v
```

Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement `app/agent/tools/score_candidate.py`**

```python
from pydantic import ValidationError
from app.types.models import Resume, JDRequirements
from app.pipeline.matcher import Matcher
from app.pipeline.reporter import Reporter

def run_score_candidate(tool_input: dict) -> dict:
    """Tool adapter: score a candidate resume against parsed JD requirements."""
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
        # reporter.generate() already returns a plain dict; ensure it here
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

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_agent_tools.py::test_score_candidate_returns_report_dict tests/test_agent_tools.py::test_score_candidate_returns_error_on_invalid_input -v
```

Expected: both PASS

- [ ] **Step 5: Commit**

```bash
git add app/agent/tools/score_candidate.py tests/test_agent_tools.py
git commit -m "feat: add score_candidate tool adapter"
```

---

### Task 4: `generate_report_html` tool

**Files:**
- Create: `app/agent/tools/generate_report_html.py`
- Test: `tests/test_agent_tools.py` (append)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_agent_tools.py`:

```python
from unittest.mock import patch
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
    # Mock subprocess so test does not depend on ui-ux-pro-max scripts
    with patch("app.agent.tools.generate_report_html.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="[]")
        result = run_generate_report_html({"report": SAMPLE_REPORT})
    assert isinstance(result, str)
    assert "<html" in result.lower()
    assert "87" in result  # overall score present

def test_generate_report_html_falls_back_when_scripts_unavailable():
    with patch("app.agent.tools.generate_report_html.subprocess.run") as mock_run:
        mock_run.side_effect = FileNotFoundError("script not found")
        result = run_generate_report_html({"report": SAMPLE_REPORT})
    assert isinstance(result, str)
    assert "<html" in result.lower()
    assert "87" in result
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_agent_tools.py::test_generate_report_html_returns_html_string -v
```

Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement `app/agent/tools/generate_report_html.py`**

```python
import json
import subprocess
from pathlib import Path

_SKILL_SCRIPT = Path.home() / ".codemaker" / "skills" / "ui-ux-pro-max" / "scripts" / "search.py"

_DEFAULT_TOKENS = {
    "heading_font": "Inter",
    "body_font": "Inter",
    "google_fonts_import": "https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap",
    "primary": "#1E3A5F",
    "accent": "#2563EB",
    "background": "#F8FAFC",
    "text": "#1E293B",
    "muted": "#64748B",
}


def _run_search(query: str, domain: str) -> list:
    """Run ui-ux-pro-max search script, return parsed JSON list or [] on any failure."""
    try:
        result = subprocess.run(
            ["python3", str(_SKILL_SCRIPT), query, "--domain", domain],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode != 0:
            return []
        return json.loads(result.stdout) if result.stdout.strip() else []
    except Exception:
        return []


def _extract_tokens(records: list, field_map: dict, tokens: dict) -> None:
    """Extract fields from first search result into tokens dict, skip if missing."""
    if not records:
        return
    first = records[0]
    for src_field, dst_key in field_map.items():
        value = first.get(src_field)
        if value:
            tokens[dst_key] = value


def _gather_design_tokens() -> dict:
    tokens = dict(_DEFAULT_TOKENS)

    product_records = _run_search("HR report professional", "product")
    _extract_tokens(product_records, {
        "description": "product_description",
    }, tokens)

    style_records = _run_search("minimal professional clean", "style")
    _extract_tokens(style_records, {
        "primary_color": "primary",
        "background": "background",
    }, tokens)

    typography_records = _run_search("corporate professional", "typography")
    _extract_tokens(typography_records, {
        "heading_font": "heading_font",
        "body_font": "body_font",
        "google_fonts_import": "google_fonts_import",
    }, tokens)

    color_records = _run_search("hr saas dashboard", "color")
    _extract_tokens(color_records, {
        "primary": "primary",
        "accent": "accent",
        "background": "background",
        "text": "text",
    }, tokens)

    return tokens


def _render_html(report: dict, tokens: dict) -> str:
    overall = report.get("overall_score", 0)
    recommendation = report.get("recommendation", "")
    reasons = report.get("reasons", [])
    dimensions = report.get("dimensions", {})

    rec_color = "#16A34A" if recommendation == "推荐" else "#DC2626"

    dim_labels = {
        "hard_skills": "技术技能",
        "experience": "工作经验",
        "education": "教育背景",
        "soft_skills": "软技能",
    }

    dim_bars = ""
    for key, label in dim_labels.items():
        dim = dimensions.get(key, {})
        score = dim.get("score", 0)
        matched = ", ".join(dim.get("matched", [])) or "—"
        dim_bars += f"""
        <div style="margin-bottom:16px;">
          <div style="display:flex;justify-content:space-between;margin-bottom:4px;">
            <span style="font-weight:600;color:{tokens['text']}">{label}</span>
            <span style="color:{tokens['accent']};font-weight:700">{score}</span>
          </div>
          <div style="background:#E2E8F0;border-radius:999px;height:8px;">
            <div style="background:{tokens['accent']};width:{score}%;height:8px;border-radius:999px;transition:width 0.6s;"></div>
          </div>
          <div style="font-size:12px;color:{tokens['muted']};margin-top:4px;">匹配项：{matched}</div>
        </div>"""

    reasons_html = "".join(f'<li style="margin-bottom:6px;">{r}</li>' for r in reasons)

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>候选人评估报告</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link href="{tokens['google_fonts_import']}" rel="stylesheet">
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: '{tokens['body_font']}', sans-serif;
      background: {tokens['background']};
      color: {tokens['text']};
      min-height: 100vh;
      padding: 40px 16px;
    }}
    .card {{
      max-width: 680px;
      margin: 0 auto;
      background: #fff;
      border-radius: 16px;
      box-shadow: 0 4px 24px rgba(0,0,0,0.08);
      overflow: hidden;
    }}
    .header {{
      background: {tokens['primary']};
      padding: 32px 40px;
      color: #fff;
    }}
    .header h1 {{
      font-family: '{tokens['heading_font']}', sans-serif;
      font-size: 20px;
      font-weight: 700;
      margin-bottom: 8px;
      opacity: 0.9;
    }}
    .score-row {{
      display: flex;
      align-items: center;
      gap: 20px;
    }}
    .score-circle {{
      width: 80px;
      height: 80px;
      border-radius: 50%;
      background: rgba(255,255,255,0.15);
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      border: 3px solid rgba(255,255,255,0.4);
    }}
    .score-num {{
      font-size: 28px;
      font-weight: 700;
      line-height: 1;
    }}
    .score-label {{
      font-size: 11px;
      opacity: 0.8;
    }}
    .badge {{
      display: inline-block;
      padding: 6px 18px;
      border-radius: 999px;
      font-weight: 700;
      font-size: 14px;
      background: {rec_color};
      color: #fff;
    }}
    .body {{ padding: 32px 40px; }}
    .section-title {{
      font-family: '{tokens['heading_font']}', sans-serif;
      font-size: 13px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: {tokens['muted']};
      margin-bottom: 16px;
    }}
    .reasons {{
      list-style: none;
      padding: 0;
    }}
    .reasons li::before {{
      content: '✓ ';
      color: #16A34A;
      font-weight: 700;
    }}
    .divider {{
      border: none;
      border-top: 1px solid #E2E8F0;
      margin: 28px 0;
    }}
    @media (max-width: 480px) {{
      .header, .body {{ padding: 24px 20px; }}
    }}
  </style>
</head>
<body>
  <div class="card">
    <div class="header">
      <h1>候选人评估报告</h1>
      <div class="score-row">
        <div class="score-circle">
          <span class="score-num">{overall}</span>
          <span class="score-label">总分</span>
        </div>
        <div>
          <div class="badge">{recommendation}</div>
        </div>
      </div>
    </div>
    <div class="body">
      <div class="section-title">各维度评分</div>
      {dim_bars}
      <hr class="divider">
      <div class="section-title">评估理由</div>
      <ul class="reasons">{reasons_html}</ul>
    </div>
  </div>
</body>
</html>"""


def run_generate_report_html(tool_input: dict) -> str:
    """Tool adapter: generate a professional HTML report from a MatchReport dict."""
    report = tool_input.get("report", tool_input)
    tokens = _gather_design_tokens()
    return _render_html(report, tokens)


TOOL_SCHEMA = {
    "name": "generate_report_html",
    "description": "根据评分报告生成专业的 HTML 评估报告页面，包含总分、维度评分条和推荐结论",
    "input_schema": {
        "type": "object",
        "properties": {
            "report": {
                "type": "object",
                "description": "由 score_candidate 返回的 MatchReport 结构体"
            }
        },
        "required": ["report"]
    }
}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_agent_tools.py::test_generate_report_html_returns_html_string tests/test_agent_tools.py::test_generate_report_html_falls_back_when_scripts_unavailable -v
```

Expected: both PASS

- [ ] **Step 5: Run all tool tests together**

```bash
pytest tests/test_agent_tools.py -v
```

Expected: all PASS

- [ ] **Step 6: Commit**

```bash
git add app/agent/tools/generate_report_html.py tests/test_agent_tools.py
git commit -m "feat: add generate_report_html tool with ui-ux-pro-max integration"
```

---

## Chunk 3: HRAgent Loop

### Task 5: `HRAgent` class

**Files:**
- Modify: `app/agent/hr_agent.py` (full implementation)
- Test: `tests/test_hr_agent.py` (create)

- [ ] **Step 1: Write the failing tests**

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
    """Agent calls all three tools and returns AgentResult."""
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
    """Agent raises AgentLoopError when loop exceeds max iterations."""
    from app.types.models import Resume

    resume = Resume(**RESUME_DICT)

    with patch("app.agent.hr_agent.Anthropic") as MockAnthropic, \
         patch("app.agent.hr_agent.run_parse_jd", return_value={}):

        mock_client = MockAnthropic.return_value
        # Always return tool_use, never end_turn
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

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_hr_agent.py::test_agent_run_completes_full_loop -v
```

Expected: FAIL with `ImportError` (hr_agent not fully implemented yet)

- [ ] **Step 3: Implement `app/agent/hr_agent.py` (full)**

```python
import json
import os
import uuid

from anthropic import Anthropic

from app.agent.tools.parse_jd import run_parse_jd, TOOL_SCHEMA as PARSE_JD_SCHEMA
from app.agent.tools.score_candidate import run_score_candidate, TOOL_SCHEMA as SCORE_SCHEMA
from app.agent.tools.generate_report_html import run_generate_report_html, TOOL_SCHEMA as HTML_SCHEMA
from app.types.models import AgentResult, MatchReport, Resume

# Module-level store: session_id -> html string (persists for process lifetime)
_html_store: dict[str, str] = {}

_SYSTEM_PROMPT = """你是一位专业的HR评估专家。你需要对候选人进行全面评估，并按以下顺序调用工具：

1. 首先调用 parse_jd 解析职位描述，获取结构化需求
2. 然后调用 score_candidate，传入候选人简历和第一步返回的需求，计算匹配分数
3. 最后调用 generate_report_html，传入第二步返回的评分报告，生成HTML报告

完成三步后，输出一段中文总结，说明评估结论和推荐理由。不要跳过任何步骤。"""

_TOOL_DISPATCH = {
    "parse_jd": run_parse_jd,
    "score_candidate": run_score_candidate,
    "generate_report_html": run_generate_report_html,
}

_TOOLS = [PARSE_JD_SCHEMA, SCORE_SCHEMA, HTML_SCHEMA]


class AgentLoopError(Exception):
    """Raised when the agent tool_use loop exceeds the maximum iteration limit."""


class HRAgent:
    def __init__(self, max_iterations: int = 10):
        self.client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.max_iterations = max_iterations

    def run(self, resume: Resume, jd_text: str) -> AgentResult:
        session_id = str(uuid.uuid4())
        messages = [
            {
                "role": "user",
                "content": f"请评估以下候选人：\n\n职位描述：{jd_text}\n\n候选人简历：{resume.model_dump_json()}"
            }
        ]

        report_dict: dict = {}
        html: str = ""
        reasoning: str = ""

        for _ in range(self.max_iterations):
            response = self.client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=4096,
                system=_SYSTEM_PROMPT,
                tools=_TOOLS,
                messages=messages,
            )

            if response.stop_reason == "end_turn":
                for block in response.content:
                    if hasattr(block, "text"):
                        reasoning = block.text
                break

            if response.stop_reason == "tool_use":
                # Append assistant message with all content blocks
                messages.append({"role": "assistant", "content": response.content})

                tool_results = []
                for block in response.content:
                    if block.type != "tool_use":
                        continue

                    handler = _TOOL_DISPATCH.get(block.name)
                    if handler is None:
                        tool_output = {"error": f"Unknown tool: {block.name}"}
                    else:
                        tool_output = handler(block.input)

                    # Capture report and html from tool outputs
                    if block.name == "score_candidate" and "overall_score" in tool_output:
                        report_dict = tool_output
                    if block.name == "generate_report_html" and isinstance(tool_output, str):
                        html = tool_output
                        tool_output = {"status": "html_generated"}

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(tool_output, ensure_ascii=False),
                    })

                messages.append({"role": "user", "content": tool_results})
        else:
            raise AgentLoopError(f"Agent loop exceeded {self.max_iterations} iterations")

        report = MatchReport(**report_dict) if report_dict else MatchReport(
            overall_score=0, dimensions={}, recommendation="不推荐", reasons=["评估失败"]
        )

        _html_store[session_id] = html

        return AgentResult(
            session_id=session_id,
            report=report,
            html=html,
            reasoning=reasoning,
        )
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_hr_agent.py -v
```

Expected: both PASS

- [ ] **Step 5: Run all tests to confirm no regressions**

```bash
pytest -v
```

Expected: all PASS

- [ ] **Step 6: Commit**

```bash
git add app/agent/hr_agent.py tests/test_hr_agent.py
git commit -m "feat: implement HRAgent tool_use loop"
```

---

## Chunk 4: API Endpoints

### Task 6: New API endpoints

**Files:**
- Modify: `app/api/routes.py`
- Test: `tests/test_api.py` (append)

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_api.py`:

```python
# Append to existing test_api.py
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
    from unittest.mock import patch, MagicMock
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

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_api.py::test_agent_match_endpoint_returns_agent_result -v
```

Expected: FAIL (endpoints not yet added)

- [ ] **Step 3: Add new endpoints to `app/api/routes.py`**

Append the following to the end of `app/api/routes.py`. Note: `os`, `Header`, `HTTPException`, and `MatchRequest` are already imported in the existing file — do not duplicate them.

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

- [ ] **Step 4: Run new endpoint tests**

```bash
pytest tests/test_api.py::test_agent_match_endpoint_returns_agent_result tests/test_api.py::test_agent_report_endpoint_returns_html tests/test_api.py::test_agent_report_endpoint_returns_404_for_unknown_session -v
```

Expected: all PASS

- [ ] **Step 5: Run full test suite**

```bash
pytest -v
```

Expected: all PASS, no regressions on existing tests

- [ ] **Step 6: Commit**

```bash
git add app/api/routes.py tests/test_api.py
git commit -m "feat: add /api/v1/agent/match and /api/v1/agent/report endpoints"
```

---

## Chunk 5: Final Verification

### Task 7: End-to-end smoke test + cleanup

**Files:**
- No new files

- [ ] **Step 1: Run full test suite one final time**

```bash
pytest -v --tb=short
```

Expected: all tests PASS

- [ ] **Step 2: Verify server starts without errors**

```bash
uvicorn app.main:app --reload &
sleep 2
curl -s http://localhost:8000/health
kill %1
```

Expected output: `{"status":"ok"}` — this is the exact response from `app/main.py:health()`.

- [ ] **Step 3: Final commit**

Only commit if `git status` shows no unexpected files. Commit each changed file explicitly:

```bash
git status
git add app/ tests/
git commit -m "feat: HR Agent skill integration complete"
```
