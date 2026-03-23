import pytest
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
        with pytest.raises(AgentLoopError):
            agent.run(resume, JD_TEXT)
