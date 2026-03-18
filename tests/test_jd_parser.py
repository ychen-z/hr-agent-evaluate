import pytest
from app.pipeline.jd_parser import JDParser
from app.types.models import JDRequirements

@pytest.fixture
def parser():
    return JDParser()

def test_parse_jd_with_all_requirements(parser):
    jd = "招聘高级后端工程师，要求熟练掌握Python或Golang，有3年以上后端开发经验，本科以上学历，具备良好的沟通能力和团队协作精神。"
    result = parser.parse(jd)
    
    assert isinstance(result, JDRequirements)
    assert "Python" in result.required_skills or "Golang" in result.required_skills
    assert result.experience_years >= 3
    assert result.education_level in ["本科", "硕士", "博士"]

def test_parse_jd_minimal(parser):
    jd = "招聘工程师"
    result = parser.parse(jd)
    
    assert isinstance(result, JDRequirements)
