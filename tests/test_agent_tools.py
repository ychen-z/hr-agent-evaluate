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
