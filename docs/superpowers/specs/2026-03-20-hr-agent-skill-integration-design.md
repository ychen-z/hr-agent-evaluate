# HR Agent Skill Integration Design

Date: 2026-03-20
Status: Approved

## Overview

Introduce an `HRAgent` class that drives a Claude `tool_use` loop, exposing three skills as callable tools:

1. `parse_jd` — wraps existing `JDParser`
2. `score_candidate` — wraps existing `Matcher` + `Reporter`
3. `generate_report_html` — new skill, uses `ui-ux-pro-max` to generate a professional HTML report

Two new API endpoints are added alongside the existing `/api/v1/match` (which remains unchanged).

---

## Goals

- Give the LLM autonomous control over when and how to call each skill
- Reuse all existing pipeline code with zero modification
- Generate a high-quality, professional HTML report via `ui-ux-pro-max` skill
- Provide a dedicated HTML endpoint so the report can be opened directly in a browser

## Non-Goals

- Replacing or modifying the existing `/api/v1/match` pipeline
- Persistence layer or database storage
- Multi-candidate batch processing (out of scope for this change)

---

## Architecture

```
POST /api/v1/agent/match
        |
        v
   HRAgent.run(resume, jd)
        |
        v
  Claude API (tool_use mode)
  +------------------------------------------+
  |  System prompt: HR evaluation expert      |
  |  Available tools:                         |
  |    1. parse_jd                            |
  |    2. score_candidate                     |
  |    3. generate_report_html               |
  +------------------------------------------+
        |  LLM decides call order autonomously
        v
  tool_use loop (max 10 rounds)
  |-- parse_jd(jd_text) -> JDRequirements
  |-- score_candidate(resume, requirements) -> MatchReport
  +-- generate_report_html(report) -> html_string
        |
        v
  AgentResult { session_id, report, html, reasoning }

GET /api/v1/agent/report/{session_id}
        |
        v
  Returns text/html response (the stored html)
```

---

## File Structure

```
app/
├── agent/
│   ├── __init__.py
│   ├── hr_agent.py                    # HRAgent class, drives tool_use loop
│   └── tools/
│       ├── __init__.py
│       ├── parse_jd.py                # Tool adapter wrapping JDParser
│       ├── score_candidate.py         # Tool adapter wrapping Matcher + Reporter
│       └── generate_report_html.py   # New skill: calls ui-ux-pro-max, returns HTML
├── api/
│   └── routes.py                      # Add two new endpoints (existing untouched)
└── types/
    └── models.py                      # Add AgentResult model
tests/
└── test_hr_agent.py                   # Tests for agent loop and all three tools
```

---

## Component Design

### HRAgent (`app/agent/hr_agent.py`)

- Initializes Anthropic client and registers all three tools with their JSON schemas
- System prompt instructs the model to act as an HR evaluation expert and call tools in logical order
- `run(resume: Resume, jd_text: str) -> AgentResult` drives the loop:
  - Sends messages to Claude with `tools` parameter
  - On `tool_use` stop reason: dispatches to the matching tool function, appends result as `tool_result` message
  - On `end_turn` stop reason: extracts final reasoning text and returns `AgentResult`
  - Hard limit of 10 iterations; raises `AgentLoopError` if exceeded
- `session_id` is a `uuid4` string generated per run; used as key for HTML storage

### Tool: `parse_jd` (`app/agent/tools/parse_jd.py`)

- Input schema: `{ "jd_text": string }`
- Implementation: instantiates `JDParser` and calls `parse(jd_text)`
- Returns: serialized `JDRequirements` dict
- Error handling: catches `JDParseError`, returns error string so Agent can retry

### Tool: `score_candidate` (`app/agent/tools/score_candidate.py`)

- Input schema: `{ "resume": Resume dict, "requirements": JDRequirements dict }`
- Implementation: instantiates `Matcher` and `Reporter`, runs both
- Returns: serialized `MatchReport` dict
- Error handling: validates input shapes with Pydantic before executing

### Tool: `generate_report_html` (`app/agent/tools/generate_report_html.py`)

- Input schema: `{ "report": MatchReport dict }`
- Implementation:
  1. Runs `ui-ux-pro-max` search scripts to gather design parameters:
     - `search.py "HR report professional" --domain product`
     - `search.py "minimal professional clean" --domain style`
     - `search.py "corporate professional" --domain typography`
     - `search.py "hr saas dashboard" --domain color`
  2. Synthesizes design tokens (colors, fonts, style)
  3. Generates self-contained HTML string with:
     - Tailwind CDN (no build step required)
     - Overall score display (large, prominent)
     - Four dimension score bars (hard skills, experience, education, soft skills)
     - Recommendation badge (推荐 / 不推荐)
     - Reasons list
  4. Returns html string
- Falls back to a minimal built-in template if `ui-ux-pro-max` scripts are unavailable

### API Endpoints (`app/api/routes.py`)

**`POST /api/v1/agent/match`**
- Auth: same `X-API-Key` header as existing endpoint
- Request body: `MatchRequest { resume: Resume, job_description: str }`
- Response: `AgentResult { session_id, report, html, reasoning }`
- Errors: 400 bad JD, 401 bad key, 503 LLM/agent failure

**`GET /api/v1/agent/report/{session_id}`**
- No auth required (session_id is treated as a capability token)
- Returns `Content-Type: text/html`
- HTML is retrieved from an in-memory dict keyed by `session_id`
- 404 if session_id not found or expired
- Note: in-memory store is per-process, no persistence across restarts (acceptable for current scope)

### Data Model (`app/types/models.py`)

```python
class AgentResult(BaseModel):
    session_id: str
    report: MatchReport
    html: str
    reasoning: str
```

---

## Error Handling

| Scenario | Behavior |
|---|---|
| JD parse fails | Agent receives error string, may retry with adjusted prompt |
| Score tool invalid input | Pydantic validation error returned as tool_result |
| ui-ux-pro-max scripts missing | Falls back to minimal HTML template |
| Agent loop exceeds 10 rounds | Raises `AgentLoopError`, API returns 503 |
| session_id not found | GET /report returns 404 |

---

## Testing

`tests/test_hr_agent.py` covers:

- `HRAgent.run()` with mocked Anthropic client (full loop simulation)
- Each tool function in isolation (unit tests)
- `generate_report_html` with mocked `ui-ux-pro-max` scripts
- `POST /api/v1/agent/match` integration test via `TestClient`
- `GET /api/v1/agent/report/{session_id}` returns valid HTML

Existing tests remain unchanged and must continue to pass.

---

## Constraints

- Python 3.10+
- Anthropic SDK `>=0.18.0` (already in `requirements.txt`)
- No new external dependencies required
- `ui-ux-pro-max` skill path: `~/.codemaker/skills/ui-ux-pro-max/scripts/search.py`
- All new code follows existing project conventions (Pydantic v2, FastAPI, pytest)
