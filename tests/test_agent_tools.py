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

from app.agent.tools.score_candidate import run_score_candidate

def test_score_candidate_returns_report_dict():
    tool_input = {
        "resume": {
            "name": "\u5f20\u4e09",
            "email": "z@example.com",
            "phone": "138",
            "education": [{"degree": "\u672c\u79d1", "major": "\u8ba1\u7b97\u673a", "school": "\u67d0\u5927\u5b66", "year": 2018}],
            "experience": [{"company": "A\u516c\u53f8", "position": "\u5de5\u7a0b\u5e08", "duration": "3\u5e74", "description": "Python\u5f00\u53d1"}],
            "skills": ["Python"],
            "soft_skills": ["\u6c9f\u901a\u80fd\u529b"]
        },
        "requirements": {
            "required_skills": ["Python"],
            "experience_years": 3,
            "education_level": "\u672c\u79d1",
            "soft_skills": ["\u6c9f\u901a\u80fd\u529b"]
        }
    }
    result = run_score_candidate(tool_input)
    assert "overall_score" in result
    assert "recommendation" in result
    assert isinstance(result["overall_score"], int)

def test_score_candidate_returns_error_on_invalid_input():
    result = run_score_candidate({"resume": {}, "requirements": {}})
    assert "error" in result

from unittest.mock import patch
from app.agent.tools.generate_report_html import run_generate_report_html

SAMPLE_REPORT = {
    "overall_score": 87,
    "dimensions": {
        "hard_skills": {"score": 90, "matched": ["Python"], "missing": [], "detail": None},
        "experience": {"score": 100, "matched": [], "missing": [], "detail": None},
        "education": {"score": 100, "matched": [], "missing": [], "detail": None},
        "soft_skills": {"score": 80, "matched": ["\u6c9f\u901a\u80fd\u529b"], "missing": [], "detail": None},
    },
    "recommendation": "\u63a8\u8350",
    "reasons": ["\u6280\u672f\u6808\u5339\u914d\u5ea6\u9ad8", "\u5de5\u4f5c\u7ecf\u9a8c\u7b26\u5408\u8981\u6c42"]
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
