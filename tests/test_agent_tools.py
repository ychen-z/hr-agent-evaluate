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
