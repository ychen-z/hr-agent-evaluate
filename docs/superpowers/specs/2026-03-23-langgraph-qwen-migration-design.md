# Design: Migrate HR Agent to LangGraph + Qwen3-32b

**Date:** 2026-03-23
**Status:** Approved

## 1. Goal

Replace the hand-rolled Anthropic SDK agent loop and the Claude-based JD parser with:

- LangGraph `create_react_agent` for the agent runtime
- Qwen3-32b via DashScope OpenAI-compatible endpoint for all LLM calls
- LangChain `ChatOpenAI` as the model adapter

All existing API endpoints and Pydantic models remain unchanged.

## 2. Decisions

| Question | Decision |
|---|---|
| Agent runtime | `langgraph.prebuilt.create_react_agent` (pin `langgraph<2.0`) |
| Model | `qwen3-32b` |
| API | DashScope OpenAI-compatible: https://dashscope.aliyuncs.com/compatible-mode/v1 |
| Auth env var | `DASHSCOPE_API_KEY` |
| JDParser LLM | Switch to Qwen3-32b (same ChatOpenAI client) |
| JDParser fallback | Remove regex fallback entirely |
| anthropic SDK | Remove from project entirely |
| Qwen thinking mode | Disabled (`extra_body={"enable_thinking": False}`) |
| Temperature | 0.1 for deterministic scoring/parsing |

## 3. Architecture

### 3.1 Shared LLM Factory (app/utils/llm.py)

New file. Single function used by both HRAgent and JDParser:

```python
def get_qwen_model() -> ChatOpenAI:
    return ChatOpenAI(
        model="qwen3-32b",
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        api_key=os.environ["DASHSCOPE_API_KEY"],
        temperature=0.1,
        max_tokens=4096,
        extra_body={"enable_thinking": False},
    )
```

### 3.2 Tools (app/agent/tools/)

All tools decorated with `@tool` from `langchain_core.tools`.
`session_id` is bound via closure in `_make_tools(session_id)`, NOT as a tool parameter.

```python
# app/agent/hr_agent.py

def _make_tools(session_id: str):
    @tool
    def score_candidate(resume: dict, requirements: dict) -> str:
        "Score a candidate resume against job requirements."
        result = _run_score(resume, requirements)
        _report_store[session_id] = result
        return json.dumps(result)

    @tool
    def generate_report_html(report: dict) -> str:
        "Generate an HTML report from the scoring result."
        html = _run_html(report)
        _html_store[session_id] = html
        return "html_generated"

    return [parse_jd_tool, score_candidate, generate_report_html]
```

`parse_jd_tool` is a module-level `@tool` (no closure needed, no side effects):
```python
@tool
def parse_jd_tool(jd_text: str) -> str:
    "Parse a job description and return structured requirements as JSON."
    ...  # returns JSON string of JDRequirements dict
```

The actual logic for `score_candidate` and `generate_report_html` is extracted into
private helper functions `_run_score(resume, requirements) -> dict` and
`_run_html(report: dict) -> str` at module level, so the closures stay thin.

### 3.3 Agent (app/agent/hr_agent.py)

```python
from langgraph.prebuilt import create_react_agent, ToolNode
from langgraph.errors import GraphRecursionError

class HRAgent:
    def run(self, resume: Resume, job_description: str) -> AgentResult:
        session_id = str(uuid.uuid4())
        model = get_qwen_model()
        tools = _make_tools(session_id)

        # ToolNode handles tool_errors — this is the correct API in langgraph>=1.0
        tool_node = ToolNode(tools, handle_tool_errors=True)
        graph = create_react_agent(model, tool_node)  # pass ToolNode, not list

        human_input = (
            "请按顺序调用工具完成招聘评估:\n"
            "1. parse_jd 解析职位描述\n"
            "2. score_candidate 评分候选人\n"
            "3. generate_report_html 生成HTML报告\n\n"
            f"职位描述:\n{job_description}\n\n"
            f"简历:\n{resume.model_dump_json()}"
        )

        try:
            result = graph.invoke(
                {"messages": [SystemMessage(SYSTEM_PROMPT), HumanMessage(human_input)]},
                config={"configurable": {"thread_id": session_id}},
            )
        except GraphRecursionError as e:
            raise AgentLoopError("Agent exceeded maximum iterations") from e

        # Extract last non-empty AIMessage as reasoning
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
        return AgentResult(session_id=session_id, report=report, html=html, reasoning=reasoning)
```

Key design notes:
- `checkpointer` omitted entirely (defaults to None) — one-shot call, no persistence needed
- `ToolNode(..., handle_tool_errors=True)` is the correct API in langgraph>=1.0;
  passing `handle_tool_errors` to `create_react_agent` was removed in v1.0
- `thread_id` in config is ignored when checkpointer is None — harmless

### 3.4 JD Parser (app/pipeline/jd_parser.py)

- Replace `anthropic.Anthropic` with `get_qwen_model()` from `app/utils/llm.py`
- Remove `_fallback_parse` method entirely
- `parse(jd_text: str) -> JDRequirements`:
  1. Build prompt asking for JSON output of `JDRequirements` fields
  2. `response = self.model.invoke([HumanMessage(prompt)])`
  3. Extract `response.content`, strip markdown fences (` ```json ` / ` ``` `)
  4. `data = json.loads(content)`
  5. Return `JDRequirements(**data)`
  6. Raise `ValueError(f"Failed to parse JD: {e}")` on any exception
- Propagates as HTTP 500 from the route (no special handler needed)

## 4. Dependencies

```
# Remove
anthropic>=0.18.0

# Add (compatible with langgraph 1.x / langchain 1.x / langchain-openai 0.3+)
langchain>=1.0,<2.0
langchain-openai>=0.3,<2.0
langgraph>=1.0,<2.0
```

**Note on `create_react_agent` deprecation:** In langgraph>=1.0, `create_react_agent`
is marked deprecated with a warning that it will move to `langchain.agents` in v2.
This implementation pins `langgraph<2.0` to avoid the breaking change. If langgraph
v2 is adopted later, the import path must be updated to `from langchain.agents import create_agent`.

## 5. Module-level Stores

`_html_store: dict[str, str]` and `_report_store: dict[str, dict]` are module-level
dicts in `app/agent/hr_agent.py`.

**Thread safety:** Safe under CPython GIL for single-worker uvicorn (default deployment).
Not safe with `uvicorn --workers N` (multiprocess). Document this limitation in a code
comment. A Redis-backed store would be needed for multi-worker deployments.

## 6. Error Handling

| Scenario | Behavior |
|---|---|
| Qwen API unreachable | Propagates from graph.invoke as exception → HTTP 500 |
| Tool raises exception | `ToolNode(handle_tool_errors=True)` catches it, returns error as ToolMessage; model may retry or report failure |
| Agent loop too long | `GraphRecursionError` caught → `AgentLoopError` → HTTP 500 |
| Agent produces no report | `AgentLoopError` in `run()` → HTTP 500 |
| `session_id` not in `_html_store` | Route returns HTTP 404 |

## 7. Files Changed

| File | Action |
|---|---|
| `requirements.txt` | Remove `anthropic`, add `langchain/langchain-openai/langgraph` with 1.x bounds |
| `app/utils/llm.py` | **New** — `get_qwen_model()` factory |
| `app/agent/hr_agent.py` | Rewrite: `create_react_agent` + `ToolNode` + `_make_tools` closure |
| `app/agent/tools/parse_jd.py` | Add `@tool`; return JSON string |
| `app/agent/tools/score_candidate.py` | Extract `_run_score()`; closure wiring moved to `_make_tools` |
| `app/agent/tools/generate_report_html.py` | Extract `_run_html()`; closure wiring moved to `_make_tools` |
| `app/pipeline/jd_parser.py` | Replace `anthropic` with `get_qwen_model()`; remove `_fallback_parse` |
| `.env.example` | Replace `ANTHROPIC_API_KEY` with `DASHSCOPE_API_KEY` |
| `app/api/routes.py` | No change |
| `app/types/models.py` | No change |

## 8. Testing Strategy

All 19 existing tests must pass after migration.

| Test file | Mock target | Notes |
|---|---|---|
| `test_jd_parser.py` | `app.utils.llm.get_qwen_model` | Return Mock with `.invoke()` returning `MagicMock(content='{"required_skills":[],...}')` |
| `test_agent_tools.py` | `JDParser.parse`, `Matcher.match`, `Reporter.generate` | Tool logic functions unchanged; test `_run_score`, `_run_html`, `parse_jd_tool` directly |
| `test_hr_agent.py` | `app.agent.hr_agent.create_react_agent` | Return Mock whose `.invoke()` returns `{"messages": [AIMessage(content="done")]}`; pre-populate `_report_store[sid]` and `_html_store[sid]` before calling `run()` |
| `test_api.py` | `app.agent.hr_agent.HRAgent.run` | Return stub `AgentResult`; no LLM calls |

Do NOT mock `ChatOpenAI.invoke` directly inside agent tests — the graph drives the
model internally and the mock would not intercept the call correctly.

## 9. .env.example

```
DASHSCOPE_API_KEY=your_dashscope_key_here
API_KEY=your_api_key_here
```

## 10. Out of Scope

- Streaming responses
- Persistent storage (cross-restart HTML/report cache)
- Switching scorer logic in the deterministic `/api/v1/match` route
- Multi-worker deployment (Redis-backed store)
- Migrating to `langchain.agents.create_agent` (langgraph v2 API)
