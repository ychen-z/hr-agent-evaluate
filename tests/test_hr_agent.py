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
        sid = config["configurable"]["thread_id"]
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
    fake_graph.invoke.return_value = {"messages": [AIMessage(content="done")]}

    with patch("app.agent.hr_agent.create_react_agent", return_value=fake_graph), \
         patch("app.agent.hr_agent.get_qwen_model"):

        from app.agent.hr_agent import HRAgent, AgentLoopError

        agent = HRAgent()
        with pytest.raises(AgentLoopError, match="score report"):
            agent.run(resume, JD_TEXT)
