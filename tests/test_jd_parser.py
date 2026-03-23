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
