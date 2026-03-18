import pytest
from app.pipeline.matcher import Matcher
from app.types.models import Resume, Education, Experience, JDRequirements

@pytest.fixture
def matcher():
    return Matcher()

def test_match_full(matcher):
    resume = Resume(
        name="张三",
        education=[Education(degree="本科", major="计算机", school="清华", year=2018)],
        experience=[Experience(company="字节", position="工程师", duration="3年", description="后端")],
        skills=["Python", "Golang"],
        soft_skills=["沟通能力", "团队协作"]
    )
    requirements = JDRequirements(
        required_skills=["Python"],
        experience_years=3,
        education_level="本科",
        soft_skills=["沟通能力"]
    )
    
    result = matcher.match(resume, requirements)
    
    assert "hard_skills" in result
    assert "experience" in result
    assert result["hard_skills"].score == 100
