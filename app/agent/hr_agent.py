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
# Known limitation: entries are never evicted; long-running processes accumulate
# one entry per request. For production use with high request volume, replace with
# a bounded cache (e.g. cachetools.LRUCache) or an external store (Redis).
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
