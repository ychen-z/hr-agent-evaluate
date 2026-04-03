import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from app.main import app

client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

from app.agent.hr_agent import _html_store
from app.types.models import AgentResult, MatchReport

AGENT_REQUEST = {
    "resume": {
        "name": "张三",
        "email": "z@example.com",
        "phone": "138",
        "education": [{"degree": "本科", "major": "计算机", "school": "某大学", "year": 2018}],
        "experience": [{"company": "A公司", "position": "工程师", "duration": "3年", "description": "Python开发"}],
        "skills": ["Python"],
        "soft_skills": ["沟通能力"]
    },
    "job_description": "招募Python工程师，3年经验，本科学历"
}


def test_agent_match_endpoint_returns_agent_result():
    mock_report = MatchReport(
        overall_score=87,
        dimensions={},
        recommendation="推荐",
        reasons=["技术栈匹配度高"]
    )
    mock_result = AgentResult(
        session_id="test-session-001",
        report=mock_report,
        html="<html>report</html>",
        reasoning="推荐该候选人"
    )

    with patch("app.api.routes.HRAgent") as MockAgent:
        MockAgent.return_value.run.return_value = mock_result
        response = client.post(
            "/api/v1/agent/match",
            json=AGENT_REQUEST,
            headers={"X-API-Key": "test-key"}
        )

    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == "test-session-001"
    assert data["report"]["overall_score"] == 87
    assert data["html"] == "<html>report</html>"


def test_agent_report_endpoint_returns_html():
    _html_store["test-session-002"] = "<html><body>report</body></html>"
    response = client.get("/api/v1/agent/report/test-session-002")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "<html>" in response.text


def test_agent_report_endpoint_returns_404_for_unknown_session():
    response = client.get("/api/v1/agent/report/nonexistent-session")
    assert response.status_code == 404
