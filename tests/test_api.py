import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_match_endpoint():
    payload = {
        "resume": {
            "name": "张三",
            "education": [{"degree": "本科", "major": "计算机", "school": "清华", "year": 2018}],
            "experience": [{"company": "字节", "position": "工程师", "duration": "3年", "description": "后端"}],
            "skills": ["Python", "Golang"],
            "soft_skills": ["沟通能力"]
        },
        "job_description": "招聘Python工程师，3年以上经验，本科"
    }
    
    response = client.post("/api/v1/match", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "overall_score" in data
    assert "recommendation" in data
