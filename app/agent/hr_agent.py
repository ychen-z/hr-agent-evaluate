import json
import os
import uuid

from anthropic import Anthropic

from app.agent.tools.parse_jd import parse_jd_tool
from app.agent.tools.score_candidate import run_score_candidate as _run_score_candidate
from app.agent.tools.generate_report_html import run_generate_report_html as _run_generate_report_html

# Adapter wrappers: translate single-dict tool_input to new signatures
def run_parse_jd(tool_input: dict) -> dict:
    import json
    result = parse_jd_tool.invoke({"jd_text": tool_input["jd_text"]})
    return json.loads(result)

def run_score_candidate(tool_input: dict) -> dict:
    try:
        return _run_score_candidate(tool_input["resume"], tool_input["requirements"])
    except (KeyError, ValueError) as e:
        return {"error": str(e)}

def run_generate_report_html(tool_input: dict) -> str:
    report = tool_input.get("report", tool_input)
    return _run_generate_report_html(report)

PARSE_JD_SCHEMA = {
    "name": "parse_jd",
    "description": "解析职位描述文本，提取结构化需求（技能、经验年限、学历、软技能）",
    "input_schema": {
        "type": "object",
        "properties": {"jd_text": {"type": "string", "description": "原始职位描述文本"}},
        "required": ["jd_text"]
    }
}
SCORE_SCHEMA = {
    "name": "score_candidate",
    "description": "根据解析后的职位需求对候选人简历进行评分，返回各维度分数和综合推荐结论",
    "input_schema": {
        "type": "object",
        "properties": {
            "resume": {"type": "object", "description": "候选人简历（Resume 结构体）"},
            "requirements": {"type": "object", "description": "由 parse_jd 返回的职位需求结构体"}
        },
        "required": ["resume", "requirements"]
    }
}
HTML_SCHEMA = {
    "name": "generate_report_html",
    "description": "根据评分报告生成专业的 HTML 评估报告页面，包含总分、维度评分条和推荐结论",
    "input_schema": {
        "type": "object",
        "properties": {"report": {"type": "object", "description": "由 score_candidate 返回的 MatchReport 结构体"}},
        "required": ["report"]
    }
}
from app.types.models import AgentResult, MatchReport, Resume

# Module-level store: session_id -> html string (persists for process lifetime)
_html_store: dict[str, str] = {}

_MODEL = "claude-3-haiku-20240307"

_SYSTEM_PROMPT = """你是一位专业的HR评估专家。你需要对候选人进行全面评估，并按以下顺序调用工具：

1. 首先调用 parse_jd 解析职位描述，获取结构化需求
2. 然后调用 score_candidate，传入候选人简历和第一步返回的需求，计算匹配分数
3. 最后调用 generate_report_html，传入第二步返回的评分报告，生成HTML报告

完成三步后，输出一段中文总结，说明评估结论和推荐理由。不要跳过任何步骤。"""

def _dispatch(tool_name: str):
    """Look up tool handler by name at call time so patches applied to module
    attributes (e.g. in tests) are respected."""
    _map = {
        "parse_jd": run_parse_jd,
        "score_candidate": run_score_candidate,
        "generate_report_html": run_generate_report_html,
    }
    return _map.get(tool_name)

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
                model=_MODEL,
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

                    handler = _dispatch(block.name)
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
