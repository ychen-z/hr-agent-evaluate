# LangGraph + Qwen3-32b Migration Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the hand-rolled Anthropic SDK agent loop and Claude-based JD parser with LangGraph `create_react_agent` + Qwen3-32b via DashScope OpenAI-compatible endpoint, keeping all API contracts unchanged.

**Architecture:** A shared `get_qwen_model()` factory (`app/utils/llm.py`) returns a `ChatOpenAI` instance pointing at DashScope. `HRAgent` uses `create_react_agent` with a list of `@tool`-decorated functions; `ToolNode(tools, handle_tool_errors=True)` is passed as the `tools` argument. `session_id` is `str(uuid.uuid4())` and is bound into stateful tools via closure in `_make_tools`. `JDParser` switches to the same `ChatOpenAI` client with regex fallback removed.

**Tech Stack:** `langgraph>=1.0,<2.0`, `langchain>=1.0,<2.0`, `langchain-openai>=0.3,<2.0`, FastAPI (unchanged), pytest (unchanged)

---

## Chunk 1: Foundation — dependencies and shared LLM factory

### Task 1: Update dependencies

**Files:**
- Modify: `requirements.txt`
- Modify: `.env.example`

- [ ] **Step 1: Edit `requirements.txt`**

Remove `anthropic>=0.18.0` and add the three LangChain/LangGraph packages:

```
fastapi>=0.104.0
uvicorn>=0.24.0
pydantic>=2.5.0
langchain>=1.0,<2.0
langchain-openai>=0.3,<2.0
langgraph>=1.0,<2.0
python-dotenv>=1.0.0
pytest>=7.4.0
pytest-asyncio>=0.21.0
httpx>=0.25.0
```

- [ ] **Step 2: Update `.env.example`**

Replace `ANTHROPIC_API_KEY` line with:

```
DASHSCOPE_API_KEY=your_dashscope_key_here
API_KEY=your_api_key_here
```

- [ ] **Step 3: Install updated dependencies**

```bash
pip install -r requirements.txt
```

Expected: no errors; `langchain`, `langchain-openai`, `langgraph` installed.

- [ ] **Step 4: Commit**

```bash
git add requirements.txt .env.example
git commit -m "chore: replace anthropic with langchain/langgraph/langchain-openai"
```

---

### Task 2: Create shared LLM factory

**Files:**
- Create: `app/utils/llm.py`
- Test: `tests/test_llm_factory.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_llm_factory.py`:

```python
import os
import pytest
from unittest.mock import patch
from langchain_openai import ChatOpenAI


def test_get_qwen_model_returns_chat_openai():
    with patch.dict(os.environ, {"DASHSCOPE_API_KEY": "test-key"}):
        from app.utils import llm as llm_mod
        import importlib; importlib.reload(llm_mod)
        model = llm_mod.get_qwen_model()
    assert isinstance(model, ChatOpenAI)
    assert model.model_name == "qwen3-32b"


def test_get_qwen_model_uses_dashscope_base_url():
    with patch.dict(os.environ, {"DASHSCOPE_API_KEY": "test-key"}):
        from app.utils import llm as llm_mod
        import importlib; importlib.reload(llm_mod)
        model = llm_mod.get_qwen_model()
    assert "dashscope" in str(model.openai_api_base).lower()


def test_get_qwen_model_raises_key_error_without_api_key():
    """get_qwen_model() must raise KeyError when DASHSCOPE_API_KEY is absent."""
    env = {k: v for k, v in os.environ.items() if k != "DASHSCOPE_API_KEY"}
    with patch.dict(os.environ, env, clear=True):
        from app.utils import llm as llm_mod
        import importlib; importlib.reload(llm_mod)
        with pytest.raises(KeyError):
            llm_mod.get_qwen_model()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_llm_factory.py -v
```

Expected: `ModuleNotFoundError` — `app/utils/llm.py` does not exist yet.

- [ ] **Step 3: Create `app/utils/llm.py`**

```python
import os
from langchain_openai import ChatOpenAI

_DASHSCOPE_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"


def get_qwen_model() -> ChatOpenAI:
    """Return a ChatOpenAI instance configured for Qwen3-32b via DashScope.

    Raises KeyError if DASHSCOPE_API_KEY is not set in the environment.
    """
    return ChatOpenAI(
        model="qwen3-32b",
        base_url=_DASHSCOPE_BASE_URL,
        api_key=os.environ["DASHSCOPE_API_KEY"],
        temperature=0.1,
        max_tokens=4096,
        extra_body={"enable_thinking": False},
    )
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_llm_factory.py -v
```

Expected: 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add app/utils/llm.py tests/test_llm_factory.py
git commit -m "feat: add get_qwen_model() factory for Qwen3-32b via DashScope"
```

---

## Chunk 2: Migrate JD Parser

### Task 3: Rewrite `JDParser` to use `ChatOpenAI`

**Files:**
- Modify: `app/pipeline/jd_parser.py`
- Modify: `tests/test_jd_parser.py`

- [ ] **Step 1: Rewrite the tests for the new `JDParser` interface**

Replace the contents of `tests/test_jd_parser.py`:

```python
import json
import pytest
from unittest.mock import patch, MagicMock
from app.types.models import JDRequirements


def _make_llm_response(data: dict) -> MagicMock:
    """Build a mock LangChain AIMessage-like response with .content as JSON string."""
    msg = MagicMock()
    msg.content = json.dumps(data, ensure_ascii=False)
    return msg


def test_parse_returns_jd_requirements():
    with patch("app.pipeline.jd_parser.get_qwen_model") as mock_factory:
        mock_factory.return_value.invoke.return_value = _make_llm_response({
            "required_skills": ["Python", "Golang"],
            "experience_years": 3,
            "education_level": "本科",
            "soft_skills": ["沟通能力"]
        })
        from app.pipeline.jd_parser import JDParser
        parser = JDParser()
        result = parser.parse("招聘Python工程师，3年经验，本科")

    assert isinstance(result, JDRequirements)
    assert "Python" in result.required_skills
    assert result.experience_years == 3
    assert result.education_level == "本科"


def test_parse_strips_markdown_fences():
    raw = "```json\n{\"required_skills\": [\"Java\"], \"experience_years\": 5, \"education_level\": \"硕士\", \"soft_skills\": []}\n```"
    with patch("app.pipeline.jd_parser.get_qwen_model") as mock_factory:
        msg = MagicMock()
        msg.content = raw
        mock_factory.return_value.invoke.return_value = msg
        from app.pipeline.jd_parser import JDParser
        parser = JDParser()
        result = parser.parse("some jd")

    assert result.education_level == "硕士"
    assert result.experience_years == 5


def test_parse_raises_value_error_on_invalid_json():
    with patch("app.pipeline.jd_parser.get_qwen_model") as mock_factory:
        msg = MagicMock()
        msg.content = "not valid json at all"
        mock_factory.return_value.invoke.return_value = msg
        from app.pipeline.jd_parser import JDParser
        parser = JDParser()
        with pytest.raises(ValueError, match="Failed to parse JD"):
            parser.parse("some jd")


def test_parse_raises_value_error_on_missing_fields():
    """Pydantic ValidationError on missing fields is wrapped as ValueError."""
    with patch("app.pipeline.jd_parser.get_qwen_model") as mock_factory:
        mock_factory.return_value.invoke.return_value = _make_llm_response({
            "required_skills": ["Python"]
            # missing experience_years, education_level, soft_skills
        })
        from app.pipeline.jd_parser import JDParser
        parser = JDParser()
        with pytest.raises(ValueError, match="Failed to parse JD"):
            parser.parse("some jd")
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_jd_parser.py -v
```

Expected: tests fail — `jd_parser.py` still imports `anthropic`.

- [ ] **Step 3: Rewrite `app/pipeline/jd_parser.py`**

Note: all exceptions (including Pydantic `ValidationError`, `json.JSONDecodeError`, `TypeError`) are caught and re-raised as `ValueError` so callers always get a consistent error type.

```python
import json
import re
from langchain_core.messages import HumanMessage
from app.types.models import JDRequirements
from app.utils.llm import get_qwen_model

_PROMPT_TEMPLATE = """从以下职位描述中提取结构化需求，返回JSON格式。

职位描述:
{jd_text}

请提取以下字段并只返回JSON，不要其他内容：
{{
  "required_skills": ["技能1", "技能2"],
  "experience_years": 0,
  "education_level": "本科",
  "soft_skills": ["软技能1"]
}}

education_level 只能是以下之一：大专、本科、硕士、博士"""


class JDParser:
    def __init__(self):
        self.model = get_qwen_model()

    def parse(self, jd_text: str) -> JDRequirements:
        """Parse a job description text into structured JDRequirements.

        Raises ValueError if the model response cannot be parsed into JDRequirements.
        """
        prompt = _PROMPT_TEMPLATE.format(jd_text=jd_text)
        try:
            response = self.model.invoke([HumanMessage(content=prompt)])
            content = response.content
            # Strip markdown fences if present: ```json ... ``` or ``` ... ```
            content = re.sub(r"^```(?:json)?\s*", "", content.strip(), flags=re.IGNORECASE)
            content = re.sub(r"\s*```$", "", content.strip())
            data = json.loads(content)
            return JDRequirements(**data)
        except Exception as e:
            raise ValueError(f"Failed to parse JD: {e}") from e
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_jd_parser.py -v
```

Expected: 4 tests PASS.

- [ ] **Step 5: Run full test suite to check for regressions**

```bash
pytest --tb=short -q
```

Expected: all previously passing tests still pass. Tests that called the real LLM directly may fail if `DASHSCOPE_API_KEY` is not set — those are expected.

- [ ] **Step 6: Commit**

```bash
git add app/pipeline/jd_parser.py tests/test_jd_parser.py
git commit -m "feat: migrate JDParser from anthropic SDK to ChatOpenAI + Qwen3-32b"
```

---

## Chunk 3: Migrate Agent Tools

### Task 4: Refactor `parse_jd` tool

**Files:**
- Modify: `app/agent/tools/parse_jd.py`

Convert `run_parse_jd` into a `@tool`-decorated function that returns a JSON string. The `TOOL_SCHEMA` constant is removed. The function is named `parse_jd_tool` internally; `name="parse_jd"` is passed to `@tool` so the model-facing tool name stays `parse_jd`.

- [ ] **Step 1: Rewrite `app/agent/tools/parse_jd.py`**

```python
import json
from langchain_core.tools import tool
from app.pipeline.jd_parser import JDParser


@tool(name="parse_jd")
def parse_jd_tool(jd_text: str) -> str:
    """解析职位描述文本，提取结构化需求（技能、经验年限、学历、软技能），返回JSON字符串。"""
    parser = JDParser()
    requirements = parser.parse(jd_text)
    return json.dumps(requirements.model_dump(), ensure_ascii=False)
```

- [ ] **Step 2: Update parse_jd tests in `tests/test_agent_tools.py`**

Replace the parse_jd section at the top of `tests/test_agent_tools.py` with:

```python
from unittest.mock import patch, MagicMock
from app.agent.tools.parse_jd import parse_jd_tool
import json
import pytest


def test_parse_jd_tool_returns_json_string():
    mock_req = MagicMock()
    mock_req.model_dump.return_value = {
        "required_skills": ["Python"],
        "experience_years": 3,
        "education_level": "本科",
        "soft_skills": ["沟通能力"]
    }
    with patch("app.agent.tools.parse_jd.JDParser") as MockParser:
        MockParser.return_value.parse.return_value = mock_req
        result = parse_jd_tool.invoke({"jd_text": "需要Python工程师，3年经验，本科"})
    data = json.loads(result)
    assert data["required_skills"] == ["Python"]
    assert data["experience_years"] == 3


def test_parse_jd_tool_propagates_exception():
    with patch("app.agent.tools.parse_jd.JDParser") as MockParser:
        MockParser.return_value.parse.side_effect = ValueError("Failed to parse JD: bad json")
        with pytest.raises(Exception):
            parse_jd_tool.invoke({"jd_text": "some jd"})
```

- [ ] **Step 3: Run parse_jd tests**

```bash
pytest tests/test_agent_tools.py::test_parse_jd_tool_returns_json_string tests/test_agent_tools.py::test_parse_jd_tool_propagates_exception -v
```

Expected: both PASS.

- [ ] **Step 4: Commit**

```bash
git add app/agent/tools/parse_jd.py tests/test_agent_tools.py
git commit -m "feat: convert parse_jd tool to LangChain @tool decorator"
```

---

### Task 5: Refactor `score_candidate` and `generate_report_html` tools

**Files:**
- Modify: `app/agent/tools/score_candidate.py`
- Modify: `app/agent/tools/generate_report_html.py`

Both files expose only their pure logic function — the `@tool` decorator and `session_id` closure are applied in `hr_agent.py`. This keeps the tool logic testable without LangChain.

- [ ] **Step 1: Rewrite `app/agent/tools/score_candidate.py`**

```python
from pydantic import ValidationError
from app.types.models import Resume, JDRequirements
from app.pipeline.matcher import Matcher
from app.pipeline.reporter import Reporter


def run_score_candidate(resume: dict, requirements: dict) -> dict:
    """Score a candidate resume against parsed JD requirements.

    Returns a MatchReport dict with overall_score, dimensions, recommendation, reasons.
    Raises ValueError on invalid input.
    """
    try:
        resume_obj = Resume(**resume)
        req_obj = JDRequirements(**requirements)
    except (ValidationError, KeyError, TypeError) as e:
        raise ValueError(f"Invalid input: {e}") from e

    matcher = Matcher()
    reporter = Reporter()
    dimension_scores = matcher.match(resume_obj, req_obj)
    report = reporter.generate(dimension_scores)
    if hasattr(report, "model_dump"):
        return report.model_dump()
    return report
```

- [ ] **Step 2: Rewrite `app/agent/tools/generate_report_html.py`**

Keep `_gather_design_tokens` and `_render_html` exactly as they are in the current file. Only remove `run_generate_report_html` wrapper's old dict-unwrapping logic and `TOOL_SCHEMA` constant. The new file ends with:

```python
def run_generate_report_html(report: dict) -> str:
    """Generate a professional HTML report from a MatchReport dict. Returns raw HTML string."""
    tokens = _gather_design_tokens()
    return _render_html(report, tokens)
```

Everything above that line (`_SKILL_SCRIPT`, `_DEFAULT_TOKENS`, `_run_search`, `_extract_tokens`, `_gather_design_tokens`, `_render_html`) is copied verbatim from the current file. Do NOT re-implement `_render_html` — copy it as-is to avoid introducing bugs.

- [ ] **Step 3: Update score_candidate and generate_report_html tests in `tests/test_agent_tools.py`**

Append the following to `tests/test_agent_tools.py` (replacing the old `run_score_candidate` and `run_generate_report_html` test blocks):

```python
import pytest
from unittest.mock import patch, MagicMock
from app.agent.tools.score_candidate import run_score_candidate
from app.agent.tools.generate_report_html import run_generate_report_html

RESUME_DICT = {
    "name": "张三",
    "email": "z@example.com",
    "phone": "138",
    "education": [{"degree": "本科", "major": "计算机", "school": "某大学", "year": 2018}],
    "experience": [{"company": "A公司", "position": "工程师", "duration": "3年", "description": "Python开发"}],
    "skills": ["Python"],
    "soft_skills": ["沟通能力"]
}
REQUIREMENTS_DICT = {
    "required_skills": ["Python"],
    "experience_years": 3,
    "education_level": "本科",
    "soft_skills": ["沟通能力"]
}
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


def test_run_score_candidate_returns_report_dict():
    result = run_score_candidate(RESUME_DICT, REQUIREMENTS_DICT)
    assert "overall_score" in result
    assert "recommendation" in result
    assert isinstance(result["overall_score"], int)


def test_run_score_candidate_raises_value_error_on_invalid_input():
    with pytest.raises(ValueError, match="Invalid input"):
        run_score_candidate({}, {})


def test_run_generate_report_html_returns_html_string():
    with patch("app.agent.tools.generate_report_html.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="[]")
        result = run_generate_report_html(SAMPLE_REPORT)
    assert isinstance(result, str)
    assert "<html" in result.lower()
    assert "87" in result


def test_run_generate_report_html_falls_back_on_error():
    with patch("app.agent.tools.generate_report_html.subprocess.run") as mock_run:
        mock_run.side_effect = FileNotFoundError
        result = run_generate_report_html(SAMPLE_REPORT)
    assert "<html" in result.lower()
    assert "87" in result
```

- [ ] **Step 4: Run tool tests**

```bash
pytest tests/test_agent_tools.py -v
```

Expected: all tool tests PASS.

- [ ] **Step 5: Commit**

```bash
git add app/agent/tools/score_candidate.py app/agent/tools/generate_report_html.py tests/test_agent_tools.py
git commit -m "feat: extract run_score_candidate and run_generate_report_html for closure wiring"
```

---

## Chunk 4: Rewrite HRAgent with LangGraph

### Task 6: Rewrite `HRAgent` using `create_react_agent`

**Files:**
- Modify: `app/agent/hr_agent.py`
- Modify: `tests/test_hr_agent.py`

**Key implementation notes:**
- `session_id = str(uuid.uuid4())` — always a string, not a UUID object
- `_make_tools` returns a list of `@tool`-decorated callables (LangGraph requires decorated tools)
- `ToolNode(tools, handle_tool_errors=True)` is passed as the `tools` argument to `create_react_agent` — this is the correct API in langgraph>=1.0 for injecting a pre-built ToolNode
- `session_id` captured by closure must be the same string used as the dict key in both `_report_store` and `_html_store`

- [ ] **Step 1: Write the new tests first**

Replace the contents of `tests/test_hr_agent.py`:

```python
import json
import pytest
from unittest.mock import MagicMock, patch
from langchain_core.messages import AIMessage
from app.types.models import Resume

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

REPORT_DICT = {
    "overall_score": 87,
    "dimensions": {},
    "recommendation": "推荐",
    "reasons": ["技术栈匹配度高"]
}


def test_agent_run_returns_agent_result():
    """HRAgent.run returns AgentResult with populated fields."""
    resume = Resume(**RESUME_DICT)

    fake_graph = MagicMock()

    def fake_invoke(messages, config):
        # Simulate tools writing to stores by populating them using the thread_id
        sid = config["configurable"]["thread_id"]
        # Import stores here to avoid circular import at module level
        from app.agent import hr_agent as agent_mod
        agent_mod._report_store[sid] = REPORT_DICT
        agent_mod._html_store[sid] = "<html>report</html>"
        return {"messages": [AIMessage(content="评估完成，推荐该候选人")]}

    fake_graph.invoke.side_effect = fake_invoke

    with patch("app.agent.hr_agent.create_react_agent", return_value=fake_graph), \
         patch("app.agent.hr_agent.get_qwen_model"):

        from app.agent.hr_agent import HRAgent, _html_store

        agent = HRAgent()
        result = agent.run(resume, JD_TEXT)

    assert result.report.overall_score == 87
    assert result.html == "<html>report</html>"
    assert "推荐" in result.reasoning
    assert result.session_id in _html_store


def test_agent_raises_agent_loop_error_on_recursion():
    """HRAgent.run raises AgentLoopError when LangGraph hits recursion limit."""
    from langgraph.errors import GraphRecursionError

    resume = Resume(**RESUME_DICT)

    fake_graph = MagicMock()
    fake_graph.invoke.side_effect = GraphRecursionError("recursion limit")

    with patch("app.agent.hr_agent.create_react_agent", return_value=fake_graph), \
         patch("app.agent.hr_agent.get_qwen_model"):

        from app.agent.hr_agent import HRAgent, AgentLoopError

        agent = HRAgent()
        with pytest.raises(AgentLoopError, match="maximum iterations"):
            agent.run(resume, JD_TEXT)


def test_agent_raises_when_report_store_empty():
    """HRAgent.run raises AgentLoopError if score_candidate tool never wrote to store."""
    resume = Resume(**RESUME_DICT)

    fake_graph = MagicMock()
    # invoke returns a valid response but does NOT populate _report_store
    fake_graph.invoke.return_value = {"messages": [AIMessage(content="done")]}

    with patch("app.agent.hr_agent.create_react_agent", return_value=fake_graph), \
         patch("app.agent.hr_agent.get_qwen_model"):

        from app.agent.hr_agent import HRAgent, AgentLoopError

        agent = HRAgent()
        with pytest.raises(AgentLoopError, match="score report"):
            agent.run(resume, JD_TEXT)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_hr_agent.py -v
```

Expected: tests fail — `hr_agent.py` still uses anthropic and the old imports.

- [ ] **Step 3: Rewrite `app/agent/hr_agent.py`**

```python
import json
import uuid

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.errors import GraphRecursionError
from langgraph.prebuilt import ToolNode, create_react_agent

from app.agent.tools.generate_report_html import run_generate_report_html
from app.agent.tools.parse_jd import parse_jd_tool
from app.agent.tools.score_candidate import run_score_candidate
from app.types.models import AgentResult, MatchReport, Resume
from app.utils.llm import get_qwen_model

# Module-level stores keyed by session_id (string).
# Safe under CPython GIL with single-worker uvicorn.
# NOT safe with uvicorn --workers N (multiprocess).
_html_store: dict[str, str] = {}
_report_store: dict[str, dict] = {}

_SYSTEM_PROMPT = """你是一位专业的HR评估专家。你需要对候选人进行全面评估，并严格按以下顺序调用工具：

1. 调用 parse_jd 解析职位描述，获取结构化需求
2. 调用 score_candidate，传入候选人简历和第一步返回的需求，计算匹配分数
3. 调用 generate_report_html，传入第二步返回的评分报告，生成HTML报告

完成三步后，输出一段中文总结，说明评估结论和推荐理由。不要跳过任何步骤。"""


class AgentLoopError(Exception):
    """Raised when the agent loop exceeds limits or fails to produce required output."""


def _make_tools(session_id: str) -> list:
    """Build tool list with session_id (string) bound via closure for stateful tools."""

    @tool
    def score_candidate(resume: dict, requirements: dict) -> str:
        """根据解析后的职位需求对候选人简历进行评分，返回各维度分数和综合推荐结论（JSON字符串）。"""
        result = run_score_candidate(resume, requirements)
        _report_store[session_id] = result
        return json.dumps(result, ensure_ascii=False)

    @tool
    def generate_report_html(report: dict) -> str:
        """根据评分报告生成专业的HTML评估报告页面，返回 'html_generated' 状态。"""
        html = run_generate_report_html(report)
        _html_store[session_id] = html
        return "html_generated"

    return [parse_jd_tool, score_candidate, generate_report_html]


class HRAgent:
    def run(self, resume: Resume, jd_text: str) -> AgentResult:
        session_id = str(uuid.uuid4())  # always a string
        model = get_qwen_model()
        tools = _make_tools(session_id)

        # ToolNode with handle_tool_errors=True: tool exceptions are caught and
        # returned to the model as ToolMessage so it can retry gracefully.
        tool_node = ToolNode(tools, handle_tool_errors=True)
        graph = create_react_agent(model, tool_node)

        human_input = (
            "请按顺序调用工具完成招聘评估:\n"
            "1. parse_jd 解析职位描述\n"
            "2. score_candidate 评分候选人\n"
            "3. generate_report_html 生成HTML报告\n\n"
            f"职位描述:\n{jd_text}\n\n"
            f"简历:\n{resume.model_dump_json()}"
        )

        try:
            result = graph.invoke(
                {"messages": [SystemMessage(content=_SYSTEM_PROMPT), HumanMessage(content=human_input)]},
                config={"configurable": {"thread_id": session_id}},
            )
        except GraphRecursionError as e:
            raise AgentLoopError("Agent exceeded maximum iterations") from e

        # Extract last non-empty AIMessage content as the reasoning summary
        reasoning = ""
        for msg in reversed(result["messages"]):
            if isinstance(msg, AIMessage) and msg.content:
                reasoning = msg.content if isinstance(msg.content, str) else str(msg.content)
                break

        report_dict = _report_store.get(session_id, {})
        html = _html_store.get(session_id, "")

        if not report_dict:
            raise AgentLoopError("Agent did not produce a score report")
        if not html:
            raise AgentLoopError("Agent did not produce an HTML report")

        report = MatchReport(**report_dict)
        return AgentResult(
            session_id=session_id,
            report=report,
            html=html,
            reasoning=reasoning,
        )
```

- [ ] **Step 4: Run agent tests**

```bash
pytest tests/test_hr_agent.py -v
```

Expected: 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add app/agent/hr_agent.py tests/test_hr_agent.py
git commit -m "feat: rewrite HRAgent with LangGraph create_react_agent + Qwen3-32b"
```

---

## Chunk 5: Verify routes and final cleanup

### Task 7: Verify API routes and run full suite

**Files:**
- Check: `app/api/routes.py` (no logic changes)
- Check: `tests/test_api.py`

- [ ] **Step 1: Verify routes module imports cleanly**

```bash
python -c "from app.api.routes import router; print('OK')"
```

Expected: `OK`. If `ImportError` appears (e.g. stale import of `run_parse_jd` or `TOOL_SCHEMA`), trace the import chain and fix the stale reference.

- [ ] **Step 2: Verify `_html_store` import still works**

```bash
python -c "from app.agent.hr_agent import _html_store; print('OK')"
```

Expected: `OK`. This import is used by `tests/test_api.py`.

- [ ] **Step 3: Run the full test suite**

```bash
pytest --tb=short -q
```

Expected: all unit tests that mock the LLM pass. Tests without a `DASHSCOPE_API_KEY` that call the real LLM (e.g. the old `test_match_endpoint` integration test which creates a real `JDParser`) will fail — that is acceptable. The minimum passing count is all tests except those that require a live API key.

If any unexpected failures appear (e.g. import errors, type errors, wrong mock targets), fix them before proceeding.

- [ ] **Step 4: Commit any fixes**

```bash
git add -A
git commit -m "fix: resolve route import errors after LangGraph migration"
```

---

### Task 8: Final cleanup

**Files:**
- Check all `app/**/*.py` for stale imports

- [ ] **Step 1: Check for stale `anthropic` imports**

```bash
grep -r "from anthropic\|import anthropic" app/ --include="*.py"
```

Expected: no output. If any remain, remove them.

- [ ] **Step 2: Check for stale `TOOL_SCHEMA` and old `run_` function references**

```bash
grep -r "TOOL_SCHEMA\|run_parse_jd" app/ --include="*.py"
```

Expected: no output. `run_score_candidate` and `run_generate_report_html` may still appear (they are imported in `hr_agent.py`) — that is correct. Only `run_parse_jd` and `TOOL_SCHEMA` should be absent.

- [ ] **Step 3: Run full test suite one final time**

```bash
pytest --tb=short -q
```

Record the final count. All mocked tests must pass.

- [ ] **Step 4: Final commit**

```bash
git add -A
git commit -m "chore: remove stale anthropic/tool-schema references after migration"
```

---

## Summary of all changed files

| File | Change |
|---|---|
| `requirements.txt` | Remove `anthropic`, add `langchain/langchain-openai/langgraph` (1.x bounds) |
| `.env.example` | Replace `ANTHROPIC_API_KEY` with `DASHSCOPE_API_KEY` |
| `app/utils/llm.py` | **New** — `get_qwen_model()` raising `KeyError` if env var absent |
| `app/pipeline/jd_parser.py` | Replace `anthropic` with `get_qwen_model()`, remove `_fallback_parse`, wrap all exceptions as `ValueError` |
| `app/agent/tools/parse_jd.py` | `@tool(name="parse_jd")` decorator, return JSON string, no `TOOL_SCHEMA` |
| `app/agent/tools/score_candidate.py` | Expose `run_score_candidate(resume, requirements) -> dict`, raise `ValueError` on invalid input |
| `app/agent/tools/generate_report_html.py` | Expose `run_generate_report_html(report) -> str`, no `TOOL_SCHEMA` |
| `app/agent/hr_agent.py` | Full rewrite: `create_react_agent` + `ToolNode` + `_make_tools` closure, `_report_store` added |
| `app/api/routes.py` | No logic change (verify imports resolve) |
| `tests/test_llm_factory.py` | **New** — 3 tests for `get_qwen_model()` |
| `tests/test_jd_parser.py` | Rewrite for `ChatOpenAI` mock pattern, 4 tests |
| `tests/test_agent_tools.py` | Update all tool tests for new signatures |
| `tests/test_hr_agent.py` | Rewrite with LangGraph mock pattern (`side_effect` populates stores) |
