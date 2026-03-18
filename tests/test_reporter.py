import pytest
from app.pipeline.reporter import Reporter
from app.types.models import DimensionScore

@pytest.fixture
def reporter():
    return Reporter()

def test_generate_report(reporter):
    dimension_scores = {
        "hard_skills": DimensionScore(score=90, matched=["Python"], missing=[]),
        "experience": DimensionScore(score=100, detail="3年 vs 要求3年"),
        "education": DimensionScore(score=100, detail="本科 vs 要求本科"),
        "soft_skills": DimensionScore(score=80, matched=["沟通能力"], missing=[])
    }
    
    result = reporter.generate(dimension_scores)
    
    assert result["overall_score"] == 93
    assert result["recommendation"] == "推荐"
    assert len(result["reasons"]) > 0
